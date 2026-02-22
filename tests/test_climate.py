"""Tests for climate entity."""
from unittest.mock import MagicMock

from custom_components.maestro_mcz.climate import MaestroClimate
from homeassistant.components.climate import HVACAction, HVACMode


def make_climate(state: dict) -> MaestroClimate:
    """Create a MaestroClimate with a mocked controller."""
    controller = MagicMock()
    controller.serial = "12345"
    controller.state = state
    controller.connected = True
    climate = MaestroClimate.__new__(MaestroClimate)
    climate._controller = controller
    return climate


class TestHvacAction:
    def test_off(self):
        climate = make_climate({"Stove_State": 0})
        assert climate.hvac_action == HVACAction.OFF

    def test_heating(self):
        climate = make_climate({"Stove_State": 11})
        assert climate.hvac_action == HVACAction.HEATING

    def test_cooling(self):
        climate = make_climate({"Stove_State": 41})
        assert climate.hvac_action == HVACAction.IDLE

    def test_none_when_unknown(self):
        climate = make_climate({})
        assert climate.hvac_action is None

    def test_invalid_value_returns_none(self):
        climate = make_climate({"Stove_State": "not_a_number"})
        assert climate.hvac_action is None


class TestHvacMode:
    def test_heat_when_on(self):
        climate = make_climate({"Power": 1})
        assert climate.hvac_mode == HVACMode.HEAT

    def test_off_when_off(self):
        climate = make_climate({"Power": 0})
        assert climate.hvac_mode == HVACMode.OFF


class TestTargetTemperature:
    def test_reads_active_set_point(self):
        climate = make_climate({"Active_Set_Point": 21.5})
        assert climate.target_temperature == 21.5

    def test_none_when_missing(self):
        climate = make_climate({})
        assert climate.target_temperature is None


class TestFanMode:
    def test_fan_level(self):
        climate = make_climate({"Fan_State": 3})
        assert climate.fan_mode == "3"

    def test_fan_auto(self):
        climate = make_climate({"Fan_State": 0})
        assert climate.fan_mode == "auto"

    def test_fan_none(self):
        climate = make_climate({})
        assert climate.fan_mode is None


class TestPresetMode:
    def test_power_level(self):
        climate = make_climate({"Stove_State": 13})
        assert climate.preset_mode == "Power 3"

    def test_no_preset_when_off(self):
        climate = make_climate({"Stove_State": 0})
        assert climate.preset_mode is None
