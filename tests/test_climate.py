"""Tests for climate entity."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.maestro_mcz.climate import MaestroClimate
from homeassistant.components.climate import HVACAction, HVACMode


def _make_climate(state: dict) -> MaestroClimate:
    """Create a MaestroClimate with a mocked controller."""
    controller = MagicMock()
    controller.serial = "12345"
    controller.state = state
    controller.connected = True
    climate = MaestroClimate.__new__(MaestroClimate)
    climate._controller = controller
    climate._attr_unique_id = f"maestro_mcz_{controller.serial}_climate"
    return climate


@pytest.fixture
def make_climate():
    """Fixture that returns a factory for creating MaestroClimate instances."""
    return _make_climate


class TestHvacAction:
    def test_off(self):
        climate = _make_climate({"Stove_State": 0})
        assert climate.hvac_action == HVACAction.OFF

    def test_heating(self):
        climate = _make_climate({"Stove_State": 11})
        assert climate.hvac_action == HVACAction.HEATING

    def test_cooling(self):
        climate = _make_climate({"Stove_State": 41})
        assert climate.hvac_action == HVACAction.IDLE

    def test_none_when_unknown(self):
        climate = _make_climate({})
        assert climate.hvac_action is None

    def test_invalid_value_returns_none(self):
        climate = _make_climate({"Stove_State": "not_a_number"})
        assert climate.hvac_action is None


class TestHvacMode:
    def test_heat_when_on(self):
        climate = _make_climate({"Power": 1})
        assert climate.hvac_mode == HVACMode.HEAT

    def test_off_when_off(self):
        climate = _make_climate({"Power": 0})
        assert climate.hvac_mode == HVACMode.OFF


class TestTargetTemperature:
    def test_reads_active_set_point(self):
        climate = _make_climate({"Active_Set_Point": 21.5})
        assert climate.target_temperature == 21.5

    def test_none_when_missing(self):
        climate = _make_climate({})
        assert climate.target_temperature is None


class TestFanMode:
    def test_fan_level(self):
        climate = _make_climate({"Fan_State": 3})
        assert climate.fan_mode == "3"

    def test_fan_auto(self):
        climate = _make_climate({"Fan_State": 0})
        assert climate.fan_mode == "auto"

    def test_fan_none(self):
        climate = _make_climate({})
        assert climate.fan_mode is None


class TestPresetMode:
    def test_power_level(self):
        climate = _make_climate({"Stove_State": 13})
        assert climate.preset_mode == "Power 3"

    def test_no_preset_when_off(self):
        climate = _make_climate({"Stove_State": 0})
        assert climate.preset_mode is None


@pytest.mark.asyncio
async def test_set_hvac_mode_heat_sends_power_command():
    """Turning on should send Power command (reg 34), not Active_Mode (reg 35)."""
    climate = _make_climate({})
    climate._controller.send_command = AsyncMock()
    await climate.async_set_hvac_mode(HVACMode.HEAT)
    climate._controller.send_command.assert_awaited_once_with("Power", 1)


@pytest.mark.asyncio
async def test_set_hvac_mode_off_sends_power_command():
    """Turning off should send Power command (reg 34), not Active_Mode (reg 35)."""
    climate = _make_climate({})
    climate._controller.send_command = AsyncMock()
    await climate.async_set_hvac_mode(HVACMode.OFF)
    climate._controller.send_command.assert_awaited_once_with("Power", 0)


def test_fan_mode_invalid_value_returns_none():
    """fan_mode should return None on non-integer state, not crash."""
    climate = _make_climate({"Fan_State": "invalid"})
    assert climate.fan_mode is None


@pytest.mark.asyncio
async def test_set_fan_mode_invalid_input():
    """async_set_fan_mode should ignore invalid fan mode strings."""
    climate = _make_climate({})
    climate._controller.send_command = AsyncMock()
    await climate.async_set_fan_mode("invalid")
    climate._controller.send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_preset_mode_invalid_input():
    """async_set_preset_mode should not crash on empty string."""
    climate = _make_climate({})
    climate._controller.send_command = AsyncMock()
    await climate.async_set_preset_mode("")
    climate._controller.send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_set_preset_mode_unknown_preset():
    """async_set_preset_mode should ignore unknown presets."""
    climate = _make_climate({})
    climate._controller.send_command = AsyncMock()
    await climate.async_set_preset_mode("Power 99")
    climate._controller.send_command.assert_not_awaited()


class TestCurrentTemperature:
    def test_reads_ambient_temperature(self, make_climate):
        climate = make_climate({"Ambient_Temperature": 22.5})
        assert climate.current_temperature == 22.5

    def test_none_when_missing(self, make_climate):
        climate = make_climate({})
        assert climate.current_temperature is None


class TestSetTemperature:
    @pytest.mark.asyncio
    async def test_sends_temperature_command(self, make_climate):
        climate = make_climate({})
        climate._controller.send_command = AsyncMock()
        await climate.async_set_temperature(temperature=22.0)
        climate._controller.send_command.assert_awaited_once_with("Temperature_Setpoint", 22.0)

    @pytest.mark.asyncio
    async def test_ignores_missing_temperature(self, make_climate):
        climate = make_climate({})
        climate._controller.send_command = AsyncMock()
        await climate.async_set_temperature()
        climate._controller.send_command.assert_not_awaited()


class TestSetFanModeValid:
    @pytest.mark.asyncio
    async def test_auto_sends_zero(self, make_climate):
        climate = make_climate({})
        climate._controller.send_command = AsyncMock()
        await climate.async_set_fan_mode("auto")
        climate._controller.send_command.assert_awaited_once_with("Fan_State", 0)

    @pytest.mark.asyncio
    async def test_numeric_mode(self, make_climate):
        climate = make_climate({})
        climate._controller.send_command = AsyncMock()
        await climate.async_set_fan_mode("3")
        climate._controller.send_command.assert_awaited_once_with("Fan_State", 3)


class TestSetPresetModeValid:
    @pytest.mark.asyncio
    async def test_power_3(self, make_climate):
        climate = make_climate({})
        climate._controller.send_command = AsyncMock()
        await climate.async_set_preset_mode("Power 3")
        climate._controller.send_command.assert_awaited_once_with("Power_Level", 3)


class TestClimateAttributes:
    def test_temperature_step(self, make_climate):
        climate = make_climate({})
        assert climate._attr_target_temperature_step == 0.5

    def test_min_temp(self, make_climate):
        climate = make_climate({})
        assert climate._attr_min_temp == 10

    def test_max_temp(self, make_climate):
        climate = make_climate({})
        assert climate._attr_max_temp == 35

    def test_unique_id(self, make_climate):
        climate = make_climate({})
        assert climate._attr_unique_id == "maestro_mcz_12345_climate"
