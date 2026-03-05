"""Tests for MaestroController."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError


class TestConvertValue:
    def test_temperature(self, controller):
        assert controller._convert_value("temperature", 43) == 21.5

    def test_temperature_zero(self, controller):
        assert controller._convert_value("temperature", 0) == 0.0

    def test_onoff_true(self, controller):
        assert controller._convert_value("onoff", 1) is True

    def test_onoff_false(self, controller):
        assert controller._convert_value("onoff", 0) is False

    def test_int_passthrough(self, controller):
        assert controller._convert_value("int", 42) == 42

    def test_timespan_passthrough(self, controller):
        assert controller._convert_value("timespan", 100) == 100


class TestGetStoveState:
    def test_known_state(self, controller):
        state = controller._get_stove_state(0)
        assert state is not None
        assert state.description == "Off"

    def test_unknown_state(self, controller):
        assert controller._get_stove_state(999) is None

    def test_error_state(self, controller):
        state = controller._get_stove_state(50)
        assert state is not None
        assert "Ignition failed" in state.description
        assert state.on_or_off == 0


class TestProcessInfoFrame:
    def test_basic_parse(self, controller):
        # Stove_State=0 (Off), Fan_State=3
        parts = ["01", "00", "03"]
        controller._process_info_frame(parts)
        assert controller.state["Stove_State"] == 0
        assert controller.state["Fan_State"] == 3

    def test_temperature_conversion(self, controller):
        # Position 6 = Ambient_Temperature, 0x2B = 43 -> 21.5C
        parts = ["01"] + ["00"] * 5 + ["2B"]
        controller._process_info_frame(parts)
        assert controller.state["Ambient_Temperature"] == 21.5

    def test_setpoint_conversion(self, controller):
        # Position 11 = Active_Set_Point, 0x2A = 42 -> 21.0C
        parts = ["01"] + ["00"] * 10 + ["2A"]
        controller._process_info_frame(parts)
        assert controller.state["Active_Set_Point"] == 21.0

    def test_invalid_hex_skipped(self, controller):
        parts = ["01", "ZZ"]
        controller._process_info_frame(parts)
        assert "Stove_State" not in controller.state

    def test_derived_fields(self, controller):
        # Stove_State=11 (Power 1) -> Stove_State_Desc, Power=1
        parts = ["01", "0B"]
        controller._process_info_frame(parts)
        assert controller.state["Stove_State_Desc"] == "Power 1"
        assert controller.state["Power"] == 1

    def test_listener_called_on_change(self, controller):
        callback = MagicMock()
        controller.add_listener(callback)
        parts = ["01", "00"]
        controller._process_info_frame(parts)
        callback.assert_called_once()

    def test_listener_not_called_without_change(self, controller):
        # First call sets state
        controller._process_info_frame(["01", "00"])
        callback = MagicMock()
        controller.add_listener(callback)
        # Second call with same data should not notify
        controller._process_info_frame(["01", "00"])
        callback.assert_not_called()


class TestSendCommand:
    @pytest.mark.asyncio
    async def test_temperature_encoding(self, controller):
        controller._connected = True
        await controller.send_command("Temperature_Setpoint", 21.5)
        controller._sio.emit.assert_called_once()
        payload = controller._sio.emit.call_args[0][1]
        assert "|43" in payload["richiesta"]

    @pytest.mark.asyncio
    async def test_onoff40_on(self, controller):
        controller._connected = True
        await controller.send_command("Power", 1)
        payload = controller._sio.emit.call_args[0][1]
        assert payload["richiesta"].endswith("|1")

    @pytest.mark.asyncio
    async def test_onoff40_off(self, controller):
        controller._connected = True
        await controller.send_command("Power", 0)
        payload = controller._sio.emit.call_args[0][1]
        assert payload["richiesta"].endswith("|40")

    @pytest.mark.asyncio
    async def test_temperature_rounding_up(self, controller):
        """Temperature 21.8 should round up to 22.0 (value 44), not truncate to 21.5 (43)."""
        controller._connected = True
        controller._sio.emit = AsyncMock()
        await controller.send_command("Temperature_Setpoint", 21.8)
        call_args = controller._sio.emit.call_args
        payload = call_args[0][1]
        # 21.8 * 2 = 43.6, round(43.6) = 44 → "C|WriteParametri|42|44"
        assert payload["richiesta"] == "C|WriteParametri|42|44"

    @pytest.mark.asyncio
    async def test_raises_when_disconnected(self, controller):
        controller._connected = False
        with pytest.raises(HomeAssistantError, match="not connected"):
            await controller.send_command("Power", 1)

    @pytest.mark.asyncio
    async def test_raises_for_unknown_command(self, controller):
        controller._connected = True
        with pytest.raises(HomeAssistantError, match="Unknown command"):
            await controller.send_command("NonExistent", 0)

    @pytest.mark.asyncio
    async def test_sends_when_connected_flag_set_but_sio_not(self, controller):
        """send_command should use _connected flag, not sio.connected (race condition fix)."""
        controller._connected = True
        controller._sio.connected = False  # Library property not yet True
        controller._sio.emit = AsyncMock()
        await controller.send_command("GetInfo", 0)
        controller._sio.emit.assert_called_once()


class TestController:
    def test_listener_snapshot_safety(self, controller):
        """Removing a listener during notification should not corrupt iteration."""
        calls = []

        def callback_a():
            calls.append("a")
            controller.remove_listener(callback_b)

        def callback_b():
            calls.append("b")

        controller.add_listener(callback_a)
        controller.add_listener(callback_b)
        controller._notify_listeners()
        assert calls == ["a", "b"]


class TestConnectGuard:
    @pytest.mark.asyncio
    async def test_duplicate_connect_prevented(self, controller):
        controller._running = True
        await controller.connect()
        controller._sio.connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates(self, controller):
        """CancelledError must not be swallowed by the reconnect loop."""
        controller._sio.connected = False
        controller._sio.connect = AsyncMock(side_effect=asyncio.CancelledError)
        with pytest.raises(asyncio.CancelledError):
            await controller.connect()


class TestReconnectResilience:
    @pytest.mark.asyncio
    async def test_retry_delay_increases(self, controller):
        """Retry delay should double after each failure (exponential backoff)."""
        controller._sio.connected = False
        controller._sio.connect = AsyncMock(side_effect=Exception("fail"))
        controller._sio.disconnect = AsyncMock()

        delays = []

        async def capture_sleep(seconds):
            delays.append(seconds)
            controller._running = False  # Stop after capturing delay

        with patch("custom_components.maestro_mcz.maestro.controller.asyncio.sleep", side_effect=capture_sleep):
            await controller.connect()

        assert delays[0] == 10  # Initial delay

        # Reset and run again to see second delay
        delays.clear()

        with patch("custom_components.maestro_mcz.maestro.controller.asyncio.sleep", side_effect=capture_sleep):
            await controller.connect()

        assert delays[0] == 20  # Doubled

    @pytest.mark.asyncio
    async def test_retry_delay_caps_at_300(self, controller):
        """Retry delay should never exceed 300 seconds."""
        controller._retry_delay = 256
        controller._sio.connected = False
        controller._sio.connect = AsyncMock(side_effect=Exception("fail"))
        controller._sio.disconnect = AsyncMock()

        delays = []

        async def capture_sleep(seconds):
            delays.append(seconds)
            controller._running = False

        with patch("custom_components.maestro_mcz.maestro.controller.asyncio.sleep", side_effect=capture_sleep):
            await controller.connect()

        assert delays[0] == 256
        assert controller._retry_delay == 300  # Capped, not 512

    @pytest.mark.asyncio
    async def test_retry_delay_resets_on_connect(self, controller):
        """Successful connection should reset retry delay to initial value."""
        controller._retry_delay = 160
        await controller._on_connect()
        assert controller._retry_delay == 10

    @pytest.mark.asyncio
    async def test_wait_called_when_already_connected(self, controller):
        """wait() must be called even if sio.connected is already True (busy-loop fix)."""
        controller._sio.connected = True
        controller._sio.wait = AsyncMock(side_effect=asyncio.CancelledError)

        with pytest.raises(asyncio.CancelledError):
            await controller.connect()

        controller._sio.wait.assert_awaited_once()
        controller._sio.connect.assert_not_called()


class TestDisconnectCleanup:
    @pytest.mark.asyncio
    async def test_state_cleared_on_disconnect(self, controller):
        """State dict must be cleared on disconnect to prevent stale data."""
        controller._state = {"Ambient_Temperature": 21.5, "Stove_State": 1}
        await controller._on_disconnect()
        assert controller._state == {}
        assert controller._connected is False

    @pytest.mark.asyncio
    async def test_listeners_notified_on_disconnect(self, controller):
        """Listeners must be notified when state is cleared on disconnect."""
        callback = MagicMock()
        controller.add_listener(callback)
        controller._state = {"Ambient_Temperature": 21.5}
        await controller._on_disconnect()
        callback.assert_called_once()


class TestOnRispondo:
    @pytest.mark.asyncio
    async def test_processes_info_message(self, controller):
        """_on_rispondo should process Info-type messages."""
        data = {"stringaRicevuta": "01|00|03"}
        await controller._on_rispondo(data)
        assert controller.state.get("Stove_State") == 0

    @pytest.mark.asyncio
    async def test_ignores_non_info_message(self, controller):
        """_on_rispondo should ignore messages that aren't Info type."""
        data = {"stringaRicevuta": "99|00|03"}
        await controller._on_rispondo(data)
        assert controller.state == {}

    @pytest.mark.asyncio
    async def test_ignores_missing_key(self, controller):
        """_on_rispondo should handle data without stringaRicevuta."""
        await controller._on_rispondo({"other": "data"})
        assert controller.state == {}

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self, controller):
        """_on_rispondo should log errors, not crash."""
        await controller._on_rispondo(None)  # Should not raise


class TestSendCommandStringHandling:
    @pytest.mark.asyncio
    async def test_on_string(self, controller):
        controller._connected = True
        controller._sio.emit = AsyncMock()
        await controller.send_command("Power", "ON")
        payload = controller._sio.emit.call_args[0][1]
        assert payload["richiesta"].endswith("|1")

    @pytest.mark.asyncio
    async def test_off_string(self, controller):
        controller._connected = True
        controller._sio.emit = AsyncMock()
        await controller.send_command("Power", "OFF")
        payload = controller._sio.emit.call_args[0][1]
        assert payload["richiesta"].endswith("|40")

    @pytest.mark.asyncio
    async def test_getinfo_command(self, controller):
        controller._connected = True
        controller._sio.emit = AsyncMock()
        await controller.send_command("GetInfo", 0)
        payload = controller._sio.emit.call_args[0][1]
        assert payload["richiesta"] == "C|RecuperoInfo"

    @pytest.mark.asyncio
    async def test_invalid_string_value_raises(self, controller):
        controller._connected = True
        with pytest.raises(HomeAssistantError, match="Invalid value"):
            await controller.send_command("Power", "invalid")


class TestOnConnect:
    @pytest.mark.asyncio
    async def test_emits_join(self, controller):
        controller._sio.emit = AsyncMock()
        await controller._on_connect()
        first_call = controller._sio.emit.call_args_list[0]
        assert first_call[0][0] == "join"
        join_data = first_call[0][1]
        assert join_data["serialNumber"] == "12345"
        assert join_data["macAddress"] == "AA:BB:CC:DD:EE:FF"

    @pytest.mark.asyncio
    async def test_requests_info_after_join(self, controller):
        controller._sio.emit = AsyncMock()
        await controller._on_connect()
        assert controller._sio.emit.call_count >= 2

    @pytest.mark.asyncio
    async def test_sets_connected_true(self, controller):
        controller._sio.emit = AsyncMock()
        await controller._on_connect()
        assert controller.connected is True

    @pytest.mark.asyncio
    async def test_getinfo_succeeds_when_sio_connected_false(self, controller):
        """_on_connect should successfully send GetInfo even when sio.connected is False (race condition)."""
        controller._sio.emit = AsyncMock()
        controller._sio.connected = False  # Simulates library timing window
        await controller._on_connect()
        # Should still emit both join and GetInfo
        assert controller._sio.emit.call_count >= 2
        chiedo_call = controller._sio.emit.call_args_list[1]
        assert chiedo_call[0][0] == "chiedo"


class TestNotifyListenersExceptionHandling:
    def test_other_listeners_called_when_one_fails(self, controller):
        """If one listener raises, others should still be called."""
        calls = []
        def bad_callback():
            raise ValueError("boom")
        def good_callback():
            calls.append("called")
        controller.add_listener(bad_callback)
        controller.add_listener(good_callback)
        controller._notify_listeners()
        assert calls == ["called"]
