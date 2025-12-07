"""Maestro MCZ Controller."""
import asyncio
import aiohttp
import logging
from typing import Callable, Optional
from datetime import datetime

from .types import (
    MaestroCommand, 
    MaestroMessageType, 
    MAESTRO_COMMANDS, 
    MAESTRO_STOVE_STATES,
    MAESTRO_INFO,
    MaestroStoveState
)

_LOGGER = logging.getLogger(__name__)

class MaestroController:
    """Maestro Controller handling Websocket connection."""

    def __init__(self, host: str, port: int = 81):
        self._host = host
        self._port = port
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._state: dict[str, any] = {}
        self._listeners: list[Callable] = []
        self._connected = False
        self._running = False
        self._reconnect_delay = 5

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def state(self) -> dict[str, any]:
        return self._state

    def add_listener(self, callback: Callable):
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)

    async def connect(self):
        """Connect to the Maestro Stove."""
        self._running = True
        self._session = aiohttp.ClientSession()
        
        while self._running:
            try:
                url = f"ws://{self._host}:{self._port}"
                _LOGGER.info(f"Connecting to Maestro at {url}")
                async with self._session.ws_connect(url) as ws:
                    self._ws = ws
                    self._connected = True
                    self._reconnect_delay = 5 # Reset delay on successful connection
                    _LOGGER.info("Connected to Maestro")
                    self._notify_listeners()

                    
                    # Request initial info
                    await self._request_info()

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._on_message(msg.data)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            _LOGGER.error(f"Websocket error: {ws.exception()}")
                            break
            except Exception as e:
                _LOGGER.error(f"Connection error: {e}")
                self._connected = False
                self._notify_listeners()
            
            if self._running:
                _LOGGER.info(f"Reconnecting in {self._reconnect_delay} seconds...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 60)

    async def disconnect(self):
        """Disconnect."""
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()

    async def _on_message(self, message: str):
        """Handle incoming message."""
        try:
            parts = message.split('|')
            if not parts:
                return

            msg_type = parts[0]
            
            if msg_type == MaestroMessageType.Info.value:
                self._process_info_frame(parts)
            elif msg_type == MaestroMessageType.Ping.value:
                pass # Pong?
        except Exception as e:
            _LOGGER.error(f"Error processing message: {e}")

    def _process_info_frame(self, parts: list[str]):
        """Process the Info frame (type 01)."""
        # parts[0] is Type, so data starts at index 1
        # The schema uses 1-based index matching the array
        
        updates = {}
        for i in range(1, len(parts)):
            if i in MAESTRO_INFO:
                info_def = MAESTRO_INFO[i]
                raw_value = int(parts[i], 16)
                processed_value = self._convert_value(info_def.message_type, raw_value)
                self._state[info_def.name] = processed_value
                updates[info_def.name] = processed_value
                
                # Special handling for Stove_State to derive Power and Diagnostics
                if info_def.name == "Stove_State":
                    stove_state = self._get_stove_state(raw_value)
                    if stove_state:
                        self._state["Stove_State_Desc"] = stove_state.description
                        self._state["Power"] = stove_state.on_or_off # Derived 0 or 1
        
        if updates:
            self._notify_listeners()

    def _convert_value(self, value_type: str, value: int):
        if value_type == "temperature":
            return float(value) / 2.0
        elif value_type == "timespan":
            # Just return seconds for now, or format string? 
            # Integration usually prefers raw values, but let's see.
            return value 
        elif value_type == "onoff":
            return value == 1
        return value

    def _get_stove_state(self, state_id: int) -> Optional[MaestroStoveState]:
        for s in MAESTRO_STOVE_STATES:
            if s.id == state_id:
                return s
        return None

    def _notify_listeners(self):
        for callback in self._listeners:
            try:
                callback()
            except Exception as e:
                _LOGGER.error(f"Error in listener: {e}")

    async def send_command(self, command_name: str, value: any):
        """Send a command to the stove."""
        if not self._ws or not self._connected:
            _LOGGER.warning("Not connected, cannot send command")
            return

        cmd_def = next((c for c in MAESTRO_COMMANDS if c.name == command_name), None)
        if not cmd_def:
            _LOGGER.error(f"Unknown command: {command_name}")
            return
            
        # Serialize command based on logic from original addon
        message = ""
        if cmd_def.category == "GetInfo":
            message = "C|RecuperoInfo"
        elif cmd_def.category == "SetDateTime":
             # Value should be "ddmmYYYYHHmm" or "NOW"
             # Simplified: we assume value is passed correctly or handle NOW in upper layer
             # For now, just pass through
             message = f"C|SalvaDataOra|{value}"
        else:
            if cmd_def.category == "Diagnostics":
                cmd_header = "C|Diagnostica|"
            else:
                cmd_header = "C|WriteParametri|"
            
            # Value transformation
            processed_value = value
            if value == "ON": processed_value = 1
            elif value == "OFF": processed_value = 0
            
            try:
                processed_value = float(processed_value)
            except ValueError:
                pass # use as is if not float compatible
                
            if cmd_def.command_type == 'temperature':
                processed_value = int(float(processed_value) * 2)
            elif cmd_def.command_type == 'onoff40':
                 processed_value = int(processed_value)
                 if processed_value == 0:
                     processed_value = 40
                 else:
                     processed_value = 1
            elif cmd_def.command_type == 'onoff' or cmd_def.command_type == 'percentage':
                 processed_value = int(processed_value)

            message = f"{cmd_header}{cmd_def.id}|{int(processed_value)}"

        _LOGGER.debug(f"Sending command: {message}")
        await self._ws.send_str(message)

    async def _request_info(self):
        """Request info update."""
        if self._ws:
             await self.send_command("GetInfo", 0)

