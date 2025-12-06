"""Switch entities for Maestro MCZ."""
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import MaestroEntity

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Maestro switch platform."""
    controller = hass.data[DOMAIN][entry.entry_id]
    
    switches = [
        MaestroSwitch(controller, "Silent_Mode", "Silent Mode", "Silent_Mode"),
        MaestroSwitch(controller, "Eco_Mode", "Eco Mode", "Eco_Mode"),
        MaestroSwitch(controller, "Sound_Effects", "Sound Effects", "Sound_Effects"),
        MaestroSwitch(controller, "Chronostat", "Chronostat", "Chronostat"),
    ]
    async_add_entities(switches)

class MaestroSwitch(MaestroEntity, SwitchEntity):
    """Maestro Switch Entity."""

    def __init__(self, controller, parameter_name: str, name: str, command_name: str):
        super().__init__(controller)
        self._parameter_name = parameter_name
        self._command_name = command_name
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{parameter_name}"

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return bool(self._controller.state.get(self._parameter_name))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._controller.send_command(self._command_name, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._controller.send_command(self._command_name, 0)
