"""Maestro MCZ Controllers."""
import asyncio
import aiohttp
import logging
import socketio
from typing import Callable, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from .types import (
    MaestroCommand, 
    MaestroMessageType, 
    MAESTRO_COMMANDS, 
    MAESTRO_STOVE_STATES,
    MAESTRO_INFO,
    MaestroStoveState
)

_LOGGER = logging.getLogger(__name__)

"""Maestro MCZ Controller."""
import asyncio
import logging
import socketio
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
    """Maestro Controller handling Cloud Socket.IO connection."""
    
    URL = "http://app.mcz.it:9000"

    def __init__(self, serial: str, mac: str):
        self._serial = serial
        self._mac = mac
        self._sio = socketio.AsyncClient(logger=False, engineio_logger=False)
        self._state: dict[str, any] = {}
        self._listeners: list[Callable] = []
        self._connected = False
        self._running = False
        
        # Register events
        self._sio.on('connect', self._on_connect)
        self._sio.on('disconnect', self._on_disconnect)
        self._sio.on('rispondo', self._on_rispondo)

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

    def _notify_listeners(self):
        for callback in self._listeners:
            try:
                callback()
            except Exception as e:
                _LOGGER.error(f"Error in listener: {e}")

    async def connect(self):
        """Connect to MCZ Cloud."""
        self._running = True
        _LOGGER.info(f"Connecting to MCZ Cloud at {self.URL} for Serial {self._serial}")
        while self._running:
            try:
                if not self._sio.connected:
                    await self._sio.connect(self.URL)
                    await self._sio.wait() # Wait until disconnected
            except Exception as e:
                _LOGGER.error(f"Cloud connection error: {e}")
                self._connected = False
                self._notify_listeners()
                await asyncio.sleep(10) # Wait before retry

    async def disconnect(self):
        self._running = False
        if self._sio.connected:
            await self._sio.disconnect()

    async def _on_connect(self):
        _LOGGER.info("Connected to MCZ Cloud")
        self._connected = True
        self._notify_listeners()
        
        # Handshake/Join
        await self._sio.emit("join", {
            "serialNumber": self._serial,
            "macAddress": self._mac,
            "type": "Android-App"
        })
        
        # Initial requests
        await self._request_info()

    async def _on_disconnect(self):
        _LOGGER.warning("Disconnected from MCZ Cloud")
        self._connected = False
        self._notify_listeners()

    async def _on_rispondo(self, data):
        """Handle 'rispondo' event."""
        # Data format: {'stringaRicevuta': '01|...'} similar to local frame
        try:
            if "stringaRicevuta" in data:
                message = data["stringaRicevuta"]
                _LOGGER.debug(f"Received cloud message: {message}")
                parts = message.split('|')
                if parts and parts[0] == MaestroMessageType.Info.value:
                    self._process_info_frame(parts)
        except Exception as e:
            _LOGGER.error(f"Error processing cloud message: {e}")

    def _process_info_frame(self, parts: list[str]):
        """Process the Info frame."""
        updates = {}
        for i in range(1, len(parts)):
            if i in MAESTRO_INFO:
                info_def = MAESTRO_INFO[i]
                raw_value = int(parts[i], 16)
                processed_value = self._convert_value(info_def.message_type, raw_value)
                self._state[info_def.name] = processed_value
                updates[info_def.name] = processed_value
                
                if info_def.name == "Stove_State":
                    stove_state = self._get_stove_state(raw_value)
                    if stove_state:
                        self._state["Stove_State_Desc"] = stove_state.description
                        self._state["Power"] = stove_state.on_or_off 
        
        if updates:
            _LOGGER.debug(f"State updates: {updates}")
            self._notify_listeners()

    async def send_command(self, command_name: str, value: any):
        """Send command via 'chiedo' event."""
        if not self._sio.connected:
            return

        cmd_def = next((c for c in MAESTRO_COMMANDS if c.name == command_name), None)
        if not cmd_def:
            return

        # Prepare payload
        payload = {
            "serialNumber": self._serial,
            "macAddress": self._mac,
            "tipoChiamata": 1, 
            "richiesta": ""
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
            if value == "ON": processed_value = 1
            elif value == "OFF": processed_value = 0
            try:
                processed_value = float(processed_value)
            except ValueError: pass
                
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

            payload["richiesta"] = f"{cmd_header}{cmd_def.id}|{int(processed_value)}"

        _LOGGER.debug(f"Sending cloud command: {payload}")
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

    def _get_stove_state(self, state_id: int) -> Optional[MaestroStoveState]:
        for s in MAESTRO_STOVE_STATES:
            if s.id == state_id:
                return s
        return None

