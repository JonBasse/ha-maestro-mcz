"""Maestro MCZ Controller."""
import asyncio
import logging
import time
from typing import Any, Callable

import socketio
from homeassistant.exceptions import HomeAssistantError

from .types import (
    MAESTRO_COMMANDS_BY_NAME,
    MAESTRO_INFO,
    MAESTRO_STOVE_STATES_BY_ID,
    MaestroMessageType,
    MaestroStoveState,
)

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = 120  # seconds between periodic GetInfo requests
RECONNECT_BASE_DELAY = 10
RECONNECT_MAX_DELAY = 300


class MaestroController:
    """Maestro Controller handling Cloud Socket.IO connection."""

    URL = "http://app.mcz.it:9000"

    def __init__(self, serial: str, mac: str):
        self._serial = serial
        self._mac = mac
        # Disable built-in reconnection — we manage our own loop
        self._sio = socketio.AsyncClient(
            logger=False, engineio_logger=False, reconnection=False,
        )
        self._state: dict[str, Any] = {}
        self._listeners: list[Callable] = []
        self._connected = False
        self._running = False
        self._retry_delay = RECONNECT_BASE_DELAY
        self._poll_task: asyncio.Task | None = None
        self._last_data_at: float = 0.0

        # Register events
        self._sio.on("connect", self._on_connect)
        self._sio.on("disconnect", self._on_disconnect)
        self._sio.on("rispondo", self._on_rispondo)

    @property
    def serial(self) -> str:
        """Return the stove serial number."""
        return self._serial

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def state(self) -> dict[str, Any]:
        return self._state

    def add_listener(self, callback: Callable):
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self):
        for callback in list(self._listeners):
            try:
                callback()
            except Exception as e:
                _LOGGER.error("Error in listener: %s", e)

    async def connect_once(self):
        """Attempt a single connection to MCZ Cloud. Raises on failure."""
        _LOGGER.info("Connecting to MCZ Cloud at %s for Serial %s", self.URL, self._serial)
        await self._sio.connect(self.URL)

    async def connect(self):
        """Connect to MCZ Cloud with automatic reconnection.

        Socket.IO's built-in ping/pong (25s interval + 20s timeout) detects
        dead connections, so we don't need an artificial timeout on wait().
        """
        if self._running:
            _LOGGER.warning("Connection loop already running, skipping duplicate")
            return
        self._running = True
        while self._running:
            try:
                if not self._sio.connected:
                    _LOGGER.info(
                        "Connecting to MCZ Cloud at %s for serial %s",
                        self.URL, self._serial,
                    )
                    await self._sio.connect(self.URL)
                # Block until the server disconnects us or the transport dies.
                # No artificial timeout — engineio ping/pong handles liveness.
                await self._sio.wait()
            except asyncio.CancelledError:
                self._running = False
                raise
            except Exception as e:
                _LOGGER.warning("Cloud connection lost: %s", e)
                self._connected = False
                self._stop_polling()
                self._notify_listeners()
                try:
                    await self._sio.disconnect()
                except Exception:
                    pass
                if self._running:
                    _LOGGER.info(
                        "Reconnecting in %ds", self._retry_delay,
                    )
                    await asyncio.sleep(self._retry_delay)
                    self._retry_delay = min(
                        self._retry_delay * 2, RECONNECT_MAX_DELAY,
                    )

    async def disconnect(self):
        self._running = False
        self._stop_polling()
        if self._sio.connected:
            await self._sio.disconnect()

    def _stop_polling(self):
        """Cancel the periodic poll task if running."""
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            self._poll_task = None

    async def _periodic_poll(self):
        """Periodically request fresh state from the stove."""
        try:
            while self._connected:
                await asyncio.sleep(POLL_INTERVAL)
                if not self._connected:
                    break
                try:
                    await self._request_info()
                    _LOGGER.debug("Periodic GetInfo poll sent")
                except Exception as e:
                    _LOGGER.warning("Periodic poll failed: %s", e)
                # Log staleness warning if no data received recently
                if self._last_data_at:
                    age = time.monotonic() - self._last_data_at
                    if age > POLL_INTERVAL * 3:
                        _LOGGER.warning(
                            "No data from stove in %.0fs despite polling", age,
                        )
        except asyncio.CancelledError:
            pass

    async def _on_connect(self):
        _LOGGER.info("Connected to MCZ Cloud for serial %s", self._serial)
        self._connected = True
        self._retry_delay = RECONNECT_BASE_DELAY
        self._notify_listeners()

        try:
            await self._sio.emit(
                "join",
                {
                    "serialNumber": self._serial,
                    "macAddress": self._mac,
                    "type": "Android-App",
                },
            )
            _LOGGER.info("Joined MCZ Cloud room, requesting initial state")
            await self._request_info()
        except Exception as e:
            _LOGGER.error("Handshake failed after connect: %s", e)

        # Start periodic polling for fresh data
        self._stop_polling()
        self._poll_task = asyncio.create_task(self._periodic_poll())

    async def _on_disconnect(self):
        _LOGGER.warning("Disconnected from MCZ Cloud (serial %s)", self._serial)
        self._connected = False
        self._stop_polling()
        # Keep last known state — entities use self.connected for availability,
        # so stale values won't be shown. Clearing state caused entities to
        # flash "unavailable" with no data during brief reconnect cycles.
        self._notify_listeners()

    async def _on_rispondo(self, data):
        """Handle 'rispondo' event."""
        try:
            self._last_data_at = time.monotonic()
            if "stringaRicevuta" in data:
                message = data["stringaRicevuta"]
                parts = message.split("|")
                msg_type = parts[0] if parts else "empty"
                _LOGGER.debug(
                    "Received cloud message type=%s len=%d",
                    msg_type, len(message),
                )
                if msg_type == MaestroMessageType.Info.value:
                    self._process_info_frame(parts)
                else:
                    _LOGGER.debug("Non-info message type: %s", msg_type)
            else:
                _LOGGER.debug(
                    "Received rispondo without stringaRicevuta: keys=%s",
                    list(data.keys()),
                )
        except Exception as e:
            _LOGGER.error("Error processing cloud message: %s", e, exc_info=True)

    def _process_info_frame(self, parts: list[str]):
        """Process the Info frame."""
        updates = {}
        for i in range(1, len(parts)):
            if i in MAESTRO_INFO:
                info_def = MAESTRO_INFO[i]
                try:
                    raw_value = int(parts[i], 16)
                except ValueError:
                    _LOGGER.warning(
                        "Invalid hex value '%s' at position %d for %s",
                        parts[i],
                        i,
                        info_def.name,
                    )
                    continue
                processed_value = self._convert_value(info_def.message_type, raw_value)
                if self._state.get(info_def.name) != processed_value:
                    self._state[info_def.name] = processed_value
                    updates[info_def.name] = processed_value

                if info_def.name == "Stove_State":
                    stove_state = self._get_stove_state(raw_value)
                    if stove_state:
                        if self._state.get("Stove_State_Desc") != stove_state.description:
                            self._state["Stove_State_Desc"] = stove_state.description
                            updates["Stove_State_Desc"] = stove_state.description
                        if self._state.get("Power") != stove_state.on_or_off:
                            self._state["Power"] = stove_state.on_or_off
                            updates["Power"] = stove_state.on_or_off

        if updates:
            _LOGGER.info("State updates (%d fields): %s", len(updates), updates)
            self._notify_listeners()

    async def send_command(self, command_name: str, value: Any):
        """Send command via 'chiedo' event."""
        if not self._connected:
            raise HomeAssistantError(
                f"Cannot send command '{command_name}': not connected to MCZ Cloud"
            )

        cmd_def = MAESTRO_COMMANDS_BY_NAME.get(command_name)
        if not cmd_def:
            raise HomeAssistantError(f"Unknown command: '{command_name}'")

        # Prepare payload
        payload = {
            "serialNumber": self._serial,
            "macAddress": self._mac,
            "tipoChiamata": 1,
            "richiesta": "",
        }

        if cmd_def.category == "GetInfo":
            payload["tipoChiamata"] = 1
            payload["richiesta"] = "C|RecuperoInfo"
        elif cmd_def.category == "SetDateTime":
            payload["tipoChiamata"] = 1
            payload["richiesta"] = f"C|SalvaDataOra|{value}"
        else:
            if cmd_def.category == "Diagnostics":
                cmd_header = "C|Diagnostica|"
            else:
                cmd_header = "C|WriteParametri|"

            processed_value = value
            if isinstance(value, str):
                if value.upper() == "ON":
                    processed_value = 1
                elif value.upper() == "OFF":
                    processed_value = 0
                else:
                    try:
                        processed_value = float(value)
                    except ValueError:
                        raise HomeAssistantError(
                            f"Invalid value '{value}' for command '{command_name}'"
                        )

            if cmd_def.command_type == "temperature":
                processed_value = round(float(processed_value) * 2)
            elif cmd_def.command_type == "onoff40":
                processed_value = 1 if int(processed_value) else 40
            elif cmd_def.command_type in ("onoff", "percentage", "int"):
                processed_value = int(processed_value)

            payload["richiesta"] = f"{cmd_header}{cmd_def.id}|{int(processed_value)}"

        _LOGGER.debug("Sending cloud command: %s", payload)
        await self._sio.emit("chiedo", payload)

    async def _request_info(self):
        await self.send_command("GetInfo", 0)

    def _convert_value(self, value_type: str, value: int):
        if value_type == "temperature":
            return float(value) / 2.0
        elif value_type == "timespan":
            return value
        elif value_type == "onoff":
            return value == 1
        return value

    def _get_stove_state(self, state_id: int) -> MaestroStoveState | None:
        return MAESTRO_STOVE_STATES_BY_ID.get(state_id)
