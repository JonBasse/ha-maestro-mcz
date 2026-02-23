"""Tests for MaestroSensor entities."""
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfTemperature

from custom_components.maestro_mcz.maestro.controller import MaestroController
from custom_components.maestro_mcz.sensor import MaestroSensor


@pytest.fixture
def mock_controller():
    ctrl = MagicMock(spec=MaestroController)
    ctrl.serial = "12345"
    ctrl.connected = True
    ctrl.state = {}
    return ctrl


class TestSensorInit:
    TEMP_CLS = SensorDeviceClass.TEMPERATURE
    TEMP_UNIT = UnitOfTemperature.CELSIUS

    def _make_temp_sensor(self, ctrl, unit=None):
        args = (ctrl, "Ambient_Temperature", "Ambient Temperature", self.TEMP_CLS)
        if unit is not None:
            return MaestroSensor(*args, unit)
        return MaestroSensor(*args)

    def test_unique_id(self, mock_controller):
        sensor = self._make_temp_sensor(mock_controller, self.TEMP_UNIT)
        assert sensor._attr_unique_id == "maestro_mcz_12345_Ambient_Temperature"

    def test_name(self, mock_controller):
        sensor = self._make_temp_sensor(mock_controller)
        assert sensor._attr_name == "Ambient Temperature"

    def test_temperature_device_class(self, mock_controller):
        sensor = self._make_temp_sensor(mock_controller, self.TEMP_UNIT)
        assert sensor._attr_device_class == SensorDeviceClass.TEMPERATURE

    def test_temperature_state_class(self, mock_controller):
        sensor = self._make_temp_sensor(mock_controller)
        assert sensor._attr_state_class == SensorStateClass.MEASUREMENT

    def test_temperature_unit(self, mock_controller):
        sensor = self._make_temp_sensor(mock_controller, self.TEMP_UNIT)
        assert sensor._attr_native_unit_of_measurement == UnitOfTemperature.CELSIUS

    def test_no_device_class(self, mock_controller):
        sensor = MaestroSensor(mock_controller, "Fan_State", "Fan State", None)
        assert sensor._attr_device_class is None

    def test_no_state_class_without_temperature(self, mock_controller):
        sensor = MaestroSensor(mock_controller, "Fan_State", "Fan State", None)
        assert not hasattr(sensor, "_attr_state_class") or sensor._attr_state_class is None


class TestSensorNativeValue:
    def _make_temp_sensor(self, ctrl):
        return MaestroSensor(
            ctrl, "Ambient_Temperature", "Ambient Temperature",
            SensorDeviceClass.TEMPERATURE,
        )

    def test_reads_from_state(self, mock_controller):
        mock_controller.state = {"Ambient_Temperature": 21.5}
        sensor = self._make_temp_sensor(mock_controller)
        assert sensor.native_value == 21.5

    def test_none_when_missing(self, mock_controller):
        mock_controller.state = {}
        sensor = self._make_temp_sensor(mock_controller)
        assert sensor.native_value is None

    def test_stove_state_desc(self, mock_controller):
        mock_controller.state = {"Stove_State_Desc": "Power 3"}
        sensor = MaestroSensor(mock_controller, "Stove_State_Desc", "Stove State", None)
        assert sensor.native_value == "Power 3"

    def test_fan_state_integer(self, mock_controller):
        mock_controller.state = {"Fan_State": 3}
        sensor = MaestroSensor(mock_controller, "Fan_State", "Fan State", None)
        assert sensor.native_value == 3
