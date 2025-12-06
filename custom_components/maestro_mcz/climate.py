"""Climate entity for Maestro MCZ."""
from typing import Optional

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MaestroEntity
from .maestro.controller import MaestroController

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Maestro climate platform."""
    controller = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MaestroClimate(controller)])

class MaestroClimate(MaestroEntity, ClimateEntity):
    """Maestro Climate Entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    
    # Optional: Add PRESET_MODE if Control_Mode is useful
    
    @property
    def current_temperature(self) -> Optional[float]:
        return self._controller.state.get("Ambient_Temperature")

    @property
    def target_temperature(self) -> Optional[float]:
        return self._controller.state.get("Temperature_Setpoint")

    @property
    def hvac_mode(self) -> HVACMode:
        # Check Power state. 0 is Off, 1 is On (roughly)
        # Power attribute is derived in controller
        val = self._controller.state.get("Power", 0)
        return HVACMode.HEAT if val == 1 else HVACMode.OFF

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
             # Command ID 42: Temperature_Setpoint
             await self._controller.send_command("Temperature_Setpoint", temp)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.HEAT:
             # Command: Active_Mode (35) -> 1 or Power (34) -> 1?
             # Original commands.py has 'Active_Mode' (35) and 'Power' (34).
             # Usually 'Active_Mode' is preferred for On/Off?
             # Or 'Power' with ID 34.
             # Original messages.py maps -1 Power to 'onoff'.
             # Let's try 'Active_Mode' first as it sounds like the toggle.
             # Actually, checking STOVE_STATES: 0=Off.
             await self._controller.send_command("Active_Mode", 1)
        elif hvac_mode == HVACMode.OFF:
             await self._controller.send_command("Active_Mode", 0)

    @property
    def unique_id(self) -> str:
        return f"{DOMAIN}_climate"
        
    @property
    def name(self) -> str:
        return "Maestro Stove"
