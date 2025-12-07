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

class MaestroBaseController(ABC):
    """Base class for Maestro Controllers."""

    def __init__(self):
        self._state: dict[str, any] = {}
        self._listeners: list[Callable] = []
        self._connected = False

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

    @abstractmethod
    async def connect(self):
        """Connect."""

    @abstractmethod
    async def disconnect(self):
        """Disconnect."""

    @abstractmethod
    async def send_command(self, command_name: str, value: any):
        """Send command."""
    
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

class MaestroLocalController(MaestroBaseController):
    """Maestro Controller handling Local Websocket connection."""

    def __init__(self, host: str, port: int = 81):
        super().__init__()
        self._host = host
        self._port = port
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._running = False
        self._reconnect_delay = 5

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
                    self._reconnect_delay = 5 
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
                pass 
        except Exception as e:
            _LOGGER.error(f"Error processing message: {e}")

    def _process_info_frame(self, parts: list[str]):
        """Process the Info frame (type 01)."""
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
            self._notify_listeners()

    async def send_command(self, command_name: str, value: any):
        """Send a command to the stove."""
        if not self._ws or not self._connected:
            _LOGGER.warning("Not connected, cannot send command")
            return

        cmd_def = next((c for c in MAESTRO_COMMANDS if c.name == command_name), None)
        if not cmd_def:
            _LOGGER.error(f"Unknown command: {command_name}")
            return
            
        message = ""
        if cmd_def.category == "GetInfo":
            message = "C|RecuperoInfo"
        elif cmd_def.category == "SetDateTime":
             message = f"C|SalvaDataOra|{value}"
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
            except ValueError:
                pass 
                
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
         await self.send_command("GetInfo", 0)


class MaestroCloudController(MaestroBaseController):
    """Maestro Controller handling Cloud Socket.IO connection."""
    
    URL = "http://app.mcz.it:9000"

    def __init__(self, serial: str, mac: str):
        super().__init__()
        self._serial = serial
        self._mac = mac
        self._sio = socketio.AsyncClient(logger=True, engineio_logger=True)
        self._running = True
        
        # Register events
        self._sio.on('connect', self._on_connect)
        self._sio.on('disconnect', self._on_disconnect)
        self._sio.on('rispondo', self._on_rispondo)
        
    async def connect(self):
        """Connect to MCZ Cloud."""
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
                parts = message.split('|')
                if parts and parts[0] == MaestroMessageType.Info.value:
                    self._process_info_frame(parts)
        except Exception as e:
            _LOGGER.error(f"Error processing cloud message: {e}")

    def _process_info_frame(self, parts: list[str]):
        """Reuse the same processing logic."""
        # This duplicates Local logic. In real world, I'd move this to Base or Mixin.
        # Repeating for simplicity in this artifact, or I can move it to Base now.
        # Moved to Base for DRY? No, _convert_value is in Base, but loop is here.
        
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
            "tipoChiamata": 1, # Default 
            "richiesta": ""
        }

        if cmd_def.category == "GetInfo":
            payload["tipoChiamata"] = 1
            payload["richiesta"] = "C|RecuperoInfo"
        elif cmd_def.category == "SetDateTime":
             payload["tipoChiamata"] = 1 # Assume 1? 
             payload["richiesta"] = f"C|SalvaDataOra|{value}"
        else:
            # Similar logic to Local
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

MaestroController = MaestroBaseController

