"""Climate entity for Maestro MCZ."""
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MaestroEntity
from .maestro.controller import MaestroController

# Stove states that indicate active heating (power levels, stabilising, start phases)
_HEATING_STATE_IDS = set(range(1, 16)) | {31}
# Stove states that indicate cooling/extinguishing
_COOLING_STATE_IDS = {40, 41, 42, 43}


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
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_min_temp = 10
    _attr_max_temp = 35
    _attr_target_temperature_step = 0.5
    _attr_fan_modes = ["1", "2", "3", "4", "5", "auto"]
    _attr_preset_modes = ["Power 1", "Power 2", "Power 3", "Power 4", "Power 5"]
    _attr_name = None

    def __init__(self, controller: MaestroController):
        super().__init__(controller)
        self._attr_unique_id = f"{DOMAIN}_{controller.serial}_climate"

    @property
    def current_temperature(self) -> float | None:
        return self._controller.state.get("Ambient_Temperature")

    @property
    def target_temperature(self) -> float | None:
        return self._controller.state.get("Active_Set_Point")

    @property
    def hvac_mode(self) -> HVACMode:
        val = self._controller.state.get("Power", 0)
        return HVACMode.HEAT if val == 1 else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the current HVAC action."""
        stove_state = self._controller.state.get("Stove_State")
        if stove_state is None:
            return None
        try:
            state_id = int(stove_state)
        except (ValueError, TypeError):
            return None
        if state_id == 0:
            return HVACAction.OFF
        if state_id in _HEATING_STATE_IDS:
            return HVACAction.HEATING
        if state_id in _COOLING_STATE_IDS:
            return HVACAction.IDLE
        return HVACAction.IDLE

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            await self._controller.send_command("Temperature_Setpoint", temp)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVACMode.HEAT:
            await self._controller.send_command("Power", 1)
        elif hvac_mode == HVACMode.OFF:
            await self._controller.send_command("Power", 0)

    @property
    def fan_mode(self) -> str | None:
        """Return the current fan mode."""
        value = self._controller.state.get("Fan_State")
        if value is None:
            return None
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            return None
        return str(int_value) if int_value > 0 else "auto"

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode based on stove power state."""
        stove_state = self._controller.state.get("Stove_State")
        if stove_state is None:
            return None
        try:
            state_id = int(stove_state)
        except (ValueError, TypeError):
            return None
        if 11 <= state_id <= 15:
            return f"Power {state_id - 10}"
        return None

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        if fan_mode == "auto":
            await self._controller.send_command("Fan_State", 0)
        elif fan_mode in self._attr_fan_modes:
            await self._controller.send_command("Fan_State", int(fan_mode))

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode (power level)."""
        if preset_mode not in (self.preset_modes or []):
            return
        level = int(preset_mode.split()[-1])
        await self._controller.send_command("Power_Level", level)
