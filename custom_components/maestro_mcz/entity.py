"""Base entity for Maestro MCZ."""
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN
from .maestro.controller import MaestroController


class MaestroEntity(Entity):
    """Base class for Maestro Entities."""

    def __init__(self, controller: MaestroController):
        self._controller = controller
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, controller.serial)},
            name="Maestro Stove",
            manufacturer="MCZ",
            model="Maestro",
        )

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self._controller.add_listener(self._update_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks."""
        self._controller.remove_listener(self._update_callback)

    def _update_callback(self):
        """Update the entity."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self._controller.connected
