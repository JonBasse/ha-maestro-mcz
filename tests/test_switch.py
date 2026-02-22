"""Tests for MaestroSwitch entities."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.maestro_mcz.switch import MaestroSwitch
from custom_components.maestro_mcz.maestro.controller import MaestroController


@pytest.fixture
def mock_controller():
    ctrl = MagicMock(spec=MaestroController)
    ctrl.serial = "12345"
    ctrl.connected = True
    ctrl.state = {}
    ctrl.send_command = AsyncMock()
    return ctrl


@pytest.fixture
def switch(mock_controller):
    return MaestroSwitch(mock_controller, "Silent_Mode", "Silent Mode", "Silent_Mode")


class TestSwitchInit:
    def test_unique_id(self, switch):
        assert switch._attr_unique_id == "maestro_mcz_12345_Silent_Mode"

    def test_name(self, switch):
        assert switch._attr_name == "Silent Mode"


class TestSwitchIsOn:
    def test_on_when_true(self, switch, mock_controller):
        mock_controller.state = {"Silent_Mode": True}
        assert switch.is_on is True

    def test_off_when_false(self, switch, mock_controller):
        mock_controller.state = {"Silent_Mode": False}
        assert switch.is_on is False

    def test_on_when_truthy_int(self, switch, mock_controller):
        mock_controller.state = {"Silent_Mode": 1}
        assert switch.is_on is True

    def test_off_when_zero(self, switch, mock_controller):
        mock_controller.state = {"Silent_Mode": 0}
        assert switch.is_on is False

    def test_none_when_missing(self, switch, mock_controller):
        mock_controller.state = {}
        assert switch.is_on is None


class TestSwitchCommands:
    @pytest.mark.asyncio
    async def test_turn_on(self, switch, mock_controller):
        await switch.async_turn_on()
        mock_controller.send_command.assert_awaited_once_with("Silent_Mode", 1)

    @pytest.mark.asyncio
    async def test_turn_off(self, switch, mock_controller):
        await switch.async_turn_off()
        mock_controller.send_command.assert_awaited_once_with("Silent_Mode", 0)

    @pytest.mark.asyncio
    async def test_different_switch_commands(self, mock_controller):
        eco = MaestroSwitch(mock_controller, "Eco_Mode", "Eco Mode", "Eco_Mode")
        await eco.async_turn_on()
        mock_controller.send_command.assert_awaited_once_with("Eco_Mode", 1)
