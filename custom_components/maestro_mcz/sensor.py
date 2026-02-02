"""Sensor entities for Maestro MCZ."""
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
    """Set up Maestro sensor platform."""
    controller: MaestroController = hass.data[DOMAIN][entry.entry_id]

    entities = [
        MaestroSensor(controller, "Stove_State_Desc", "Stove State", None),
        MaestroSensor(controller, "Fume_Temperature", "Fume Temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
        MaestroSensor(controller, "Ambient_Temperature", "Ambient Temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS),
        MaestroSensor(controller, "Fan_State", "Fan State", None),
    ]
    async_add_entities(entities)


class MaestroSensor(MaestroEntity, SensorEntity):
    """Maestro Sensor Entity."""

    def __init__(
        self,
        controller: MaestroController,
        parameter_name: str,
        name: str,
        device_class: SensorDeviceClass | None = None,
        unit_of_measurement: str | None = None,
    ):
        super().__init__(controller)
        self._parameter_name = parameter_name
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{controller.serial}_{parameter_name}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        if device_class == SensorDeviceClass.TEMPERATURE:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self._controller.state.get(self._parameter_name)
