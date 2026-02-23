"""Tests for config flow validation."""
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SERIAL_PATTERN = r"^\d+$"
MAC_PATTERN = r"^([0-9A-F]{2}[:\-]){5}[0-9A-F]{2}$"


class TestSerialValidation:
    def test_valid_serial(self):
        assert re.match(SERIAL_PATTERN, "12345678")

    def test_serial_with_letters(self):
        assert not re.match(SERIAL_PATTERN, "1234abc")

    def test_empty_serial(self):
        assert not re.match(SERIAL_PATTERN, "")

    def test_serial_with_spaces(self):
        assert not re.match(SERIAL_PATTERN, "123 456")


class TestMacValidation:
    def test_valid_mac_colons(self):
        assert re.match(MAC_PATTERN, "AA:BB:CC:DD:EE:FF")

    def test_valid_mac_dashes(self):
        assert re.match(MAC_PATTERN, "AA-BB-CC-DD-EE-FF")

    def test_lowercase_rejected(self):
        assert not re.match(MAC_PATTERN, "aa:bb:cc:dd:ee:ff")

    def test_invalid_mac_short(self):
        assert not re.match(MAC_PATTERN, "AA:BB:CC")

    def test_invalid_mac_no_separator(self):
        assert not re.match(MAC_PATTERN, "AABBCCDDEEFF")


@pytest.mark.asyncio
async def test_config_flow_disconnects_on_failure():
    """Controller.disconnect() must be called when connect_once() fails."""
    mock_controller = MagicMock()
    mock_controller.connect_once = AsyncMock(side_effect=Exception("connection refused"))
    mock_controller.disconnect = AsyncMock()

    with patch(
        "custom_components.maestro_mcz.config_flow.MaestroController",
        return_value=mock_controller,
    ):
        from custom_components.maestro_mcz.config_flow import ConfigFlow

        flow = ConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()

        result = await flow.async_step_user(
            {"serial": "12345", "mac": "AA:BB:CC:DD:EE:FF"}
        )

    mock_controller.disconnect.assert_awaited_once()
    assert result["errors"]["base"] == "cannot_connect"
