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
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_min_temp = 10
    _attr_max_temp = 35
    _attr_name = None

    def __init__(self, controller: MaestroController):
        super().__init__(controller)
        self._attr_unique_id = f"{DOMAIN}_{controller.serial}_climate"

    @property
    def current_temperature(self) -> float | None:
        return self._controller.state.get("Ambient_Temperature")

    @property
    def target_temperature(self) -> float | None:
        return self._controller.state.get("Temperature_Setpoint")

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
        state_id = int(stove_state)
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
            await self._controller.send_command("Active_Mode", 1)
        elif hvac_mode == HVACMode.OFF:
            await self._controller.send_command("Active_Mode", 0)
