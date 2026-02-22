# Remaining Backlog Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all 7 remaining GitHub issues (#1, #3, #4, #5, #6, #8, #9) covering security docs, input validation, error handling, performance, new features, tests, and CI.

**Architecture:** Work bottom-up — fix core infrastructure first (types.py, controller.py), then entities (climate, config_flow), then add tests and CI on top. Each task is one commit.

**Tech Stack:** Python 3.12, Home Assistant 2025.1.0+, python-socketio, pytest, pytest-asyncio, ruff, GitHub Actions

---

### Task 1: Performance — dict lookups and state change detection (#6)

**Files:**
- Modify: `custom_components/maestro_mcz/maestro/types.py:46-87` (add lookup dicts after lists)
- Modify: `custom_components/maestro_mcz/maestro/types.py:61,67` (document duplicate IDs)
- Modify: `custom_components/maestro_mcz/maestro/controller.py:7-14` (import new dicts)
- Modify: `custom_components/maestro_mcz/maestro/controller.py:127-155` (state change detection)
- Modify: `custom_components/maestro_mcz/maestro/controller.py:157-166` (dict lookup for commands)
- Modify: `custom_components/maestro_mcz/maestro/controller.py:226-230` (dict lookup for states)

**Step 1: Add lookup dicts to types.py**

After `MAESTRO_COMMANDS` list (line 87), add:
```python
# Lookup by name. Note: Power (id=34) and Feeding_Screw (id=34) share an ID,
# as do Profile (id=149) and Adaptive_Mode (id=149). This is intentional —
# they are the same hardware register accessed with different value types.
MAESTRO_COMMANDS_BY_NAME: dict[str, MaestroCommand] = {
    c.name: c for c in MAESTRO_COMMANDS
}
```

After `MAESTRO_STOVE_STATES` list (line 138), add:
```python
MAESTRO_STOVE_STATES_BY_ID: dict[int, MaestroStoveState] = {
    s.id: s for s in MAESTRO_STOVE_STATES
}
```

**Step 2: Update controller.py imports**

Add `MAESTRO_COMMANDS_BY_NAME` and `MAESTRO_STOVE_STATES_BY_ID` to the imports. Remove `MAESTRO_COMMANDS` and `MAESTRO_STOVE_STATES` from imports (no longer used directly).

**Step 3: Replace linear scans in controller.py**

In `send_command` (line 163), replace:
```python
cmd_def = next((c for c in MAESTRO_COMMANDS if c.name == command_name), None)
```
with:
```python
cmd_def = MAESTRO_COMMANDS_BY_NAME.get(command_name)
```

Replace entire `_get_stove_state` method (lines 226-230):
```python
def _get_stove_state(self, state_id: int) -> MaestroStoveState | None:
    return MAESTRO_STOVE_STATES_BY_ID.get(state_id)
```

**Step 4: Add state change detection in _process_info_frame**

Replace the state assignment block (lines 143-145):
```python
processed_value = self._convert_value(info_def.message_type, raw_value)
self._state[info_def.name] = processed_value
updates[info_def.name] = processed_value
```
with:
```python
processed_value = self._convert_value(info_def.message_type, raw_value)
if self._state.get(info_def.name) != processed_value:
    self._state[info_def.name] = processed_value
    updates[info_def.name] = processed_value
```

Also update the Stove_State derived fields (lines 147-151) with change detection:
```python
if info_def.name == "Stove_State":
    stove_state = self._get_stove_state(raw_value)
    if stove_state:
        if self._state.get("Stove_State_Desc") != stove_state.description:
            self._state["Stove_State_Desc"] = stove_state.description
            updates["Stove_State_Desc"] = stove_state.description
        if self._state.get("Power") != stove_state.on_or_off:
            self._state["Power"] = stove_state.on_or_off
            updates["Power"] = stove_state.on_or_off
```

**Step 5: Commit**
```
fix: use dict lookups and add state change detection (#6)
```

---

### Task 2: Error handling — send_command, handshake, casting (#5)

**Files:**
- Modify: `custom_components/maestro_mcz/maestro/controller.py:92-108` (handshake try/except)
- Modify: `custom_components/maestro_mcz/maestro/controller.py:157-212` (send_command errors + value casting)
- Modify: `custom_components/maestro_mcz/climate.py:64-77` (hvac_action safety)

**Step 1: Wrap _on_connect handshake in try/except**

Replace lines 92-108:
```python
async def _on_connect(self):
    _LOGGER.info("Connected to MCZ Cloud")
    self._connected = True
    self._notify_listeners()

    try:
        await self._sio.emit(
            "join",
            {
                "serialNumber": self._serial,
                "macAddress": self._mac,
                "type": "Android-App",
            },
        )
        await self._request_info()
    except Exception as e:
        _LOGGER.error("Handshake failed after connect: %s", e)
```

**Step 2: Make send_command raise on failure instead of silent return**

At the top of the file, add import:
```python
from homeassistant.exceptions import HomeAssistantError
```

Replace the disconnected guard (lines 158-161):
```python
if not self._sio.connected:
    raise HomeAssistantError(
        f"Cannot send command '{command_name}': not connected to MCZ Cloud"
    )
```

Replace the unknown command guard (lines 163-166):
```python
if not cmd_def:
    raise HomeAssistantError(f"Unknown command: '{command_name}'")
```

**Step 3: Clean up value casting in send_command**

Replace the fragile casting block (lines 188-207):
```python
processed_value = value
if isinstance(value, str):
    if value.upper() == "ON":
        processed_value = 1
    elif value.upper() == "OFF":
        processed_value = 0
    else:
        try:
            processed_value = float(value)
        except ValueError:
            raise HomeAssistantError(
                f"Invalid value '{value}' for command '{command_name}'"
            )

if cmd_def.command_type == "temperature":
    processed_value = int(float(processed_value) * 2)
elif cmd_def.command_type == "onoff40":
    processed_value = 1 if int(processed_value) else 40
elif cmd_def.command_type in ("onoff", "percentage", "int"):
    processed_value = int(processed_value)
```

**Step 4: Add safety to hvac_action int cast**

Replace line 70 in climate.py:
```python
state_id = int(stove_state)
```
with:
```python
try:
    state_id = int(stove_state)
except (ValueError, TypeError):
    return None
```

**Step 5: Commit**
```
fix: improve error handling for commands, handshake, and casting (#5)
```

---

### Task 3: Input validation in config flow (#4)

**Files:**
- Modify: `custom_components/maestro_mcz/config_flow.py:1-2` (add `import re`)
- Modify: `custom_components/maestro_mcz/config_flow.py:35-41` (add validation)
- Modify: `custom_components/maestro_mcz/strings.json` (add error strings)
- Modify: `custom_components/maestro_mcz/translations/en.json` (add error strings)

**Step 1: Add regex validation before connection attempt**

Add `import re` at top of config_flow.py.

Replace lines 36-41:
```python
serial = user_input["serial"].strip()
mac = user_input["mac"].strip().upper()

if not re.match(r"^\d+$", serial):
    errors["serial"] = "invalid_serial"
elif not re.match(
    r"^([0-9A-F]{2}[:\-]){5}[0-9A-F]{2}$", mac
):
    errors["mac"] = "invalid_mac"
else:
    # Prevent duplicate entries for the same stove
    await self.async_set_unique_id(serial)
    self._abort_if_unique_id_configured()

    # Validate connection to MCZ Cloud
    controller = MaestroController(serial, mac)
    try:
        async with asyncio.timeout(10):
            await controller.connect_once()
        await controller.disconnect()
    except Exception:
        _LOGGER.exception("Failed to connect to MCZ Cloud during setup")
        errors["base"] = "cannot_connect"
    else:
        return self.async_create_entry(
            title=f"Maestro Cloud ({serial})",
            data={
                "connection_type": "cloud",
                "serial": serial,
                "mac": mac,
            },
        )
```

**Step 2: Add error strings to strings.json and en.json**

Add to the `"error"` object in both files:
```json
"invalid_serial": "Serial number must contain only digits.",
"invalid_mac": "MAC address must be in XX:XX:XX:XX:XX:XX format."
```

**Step 3: Commit**
```
feat: validate serial and MAC format in config flow (#4)
```

---

### Task 4: Climate features — fan mode and power presets (#8)

**Files:**
- Modify: `custom_components/maestro_mcz/climate.py` (add FAN_MODE, PRESET_MODE)
- Modify: `custom_components/maestro_mcz/config_flow.py` (add options flow)

**Step 1: Add fan mode and preset mode to MaestroClimate**

Update imports at top of climate.py — no new imports needed, features already imported.

Update the class attributes:
```python
_attr_supported_features = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TURN_ON
    | ClimateEntityFeature.FAN_MODE
    | ClimateEntityFeature.PRESET_MODE
)
_attr_fan_modes = ["1", "2", "3", "4", "5", "auto"]
_attr_preset_modes = ["Power 1", "Power 2", "Power 3", "Power 4", "Power 5"]
```

Add these properties and methods after `async_set_hvac_mode`:
```python
@property
def fan_mode(self) -> str | None:
    value = self._controller.state.get("Fan_State")
    if value is None:
        return None
    return str(int(value)) if int(value) > 0 else "auto"

@property
def preset_mode(self) -> str | None:
    stove_state = self._controller.state.get("Stove_State")
    if stove_state is None:
        return None
    try:
        state_id = int(stove_state)
    except (ValueError, TypeError):
        return None
    if 11 <= state_id <= 15:
        return f"Power {state_id - 10}"
    return None

async def async_set_fan_mode(self, fan_mode: str) -> None:
    if fan_mode == "auto":
        await self._controller.send_command("Fan_State", 0)
    else:
        await self._controller.send_command("Fan_State", int(fan_mode))

async def async_set_preset_mode(self, preset_mode: str) -> None:
    level = int(preset_mode.split()[-1])
    await self._controller.send_command("Power_Level", level)
```

**Step 2: Add options flow to config_flow.py**

Add `OptionsFlow` class to config_flow.py:
```python
@staticmethod
@config_entries.HANDLERS.get(DOMAIN)  # Not needed; use class method below
```

Actually, add to the `ConfigFlow` class:
```python
@staticmethod
def async_get_options_flow(config_entry: config_entries.ConfigEntry):
    return MaestroOptionsFlow(config_entry)
```

Then add a new class after ConfigFlow:
```python
class MaestroOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Maestro MCZ."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            serial = user_input["serial"].strip()
            mac = user_input["mac"].strip().upper()

            if not re.match(r"^\d+$", serial):
                errors["serial"] = "invalid_serial"
            elif not re.match(r"^([0-9A-F]{2}[:\-]){5}[0-9A-F]{2}$", mac):
                errors["mac"] = "invalid_mac"
            else:
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data={**self._config_entry.data, "serial": serial, "mac": mac},
                )
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("serial", default=self._config_entry.data.get("serial", "")): str,
                    vol.Required("mac", default=self._config_entry.data.get("mac", "")): str,
                }
            ),
            errors=errors,
        )
```

Add options flow strings to `strings.json` and `translations/en.json`:
```json
"options": {
    "step": {
        "init": {
            "title": "Reconfigure MCZ Maestro Stove",
            "data": {
                "serial": "Serial Number",
                "mac": "MAC Address"
            }
        }
    },
    "error": {
        "invalid_serial": "Serial number must contain only digits.",
        "invalid_mac": "MAC address must be in XX:XX:XX:XX:XX:XX format."
    }
}
```

**Step 3: Commit**
```
feat: add fan mode, power presets, and options flow (#8)
```

---

### Task 5: Documentation — security section and pin dependency (#1, #9)

**Files:**
- Modify: `README.md` (add security section)
- Modify: `custom_components/maestro_mcz/manifest.json:13` (pin upper bound)
- Modify: `custom_components/maestro_mcz/entity.py:29-31` (schedule_update_ha_state fix from #7 leftover)

**Step 1: Add security section to README**

After the "Troubleshooting" section, add:
```markdown
## Security Considerations

- **Unencrypted connection**: The MCZ cloud endpoint (`app.mcz.it:9000`) uses plain HTTP. This is a limitation of the MCZ cloud server — the official MCZ Maestro app also uses HTTP. Serial numbers and MAC addresses are transmitted in cleartext.
- **Credential model**: Access is controlled by serial number and MAC address only (no username/password). Anyone with these values can control the stove.
- **Config storage**: Credentials are stored in Home Assistant's config entries (standard HA behavior, encrypted at rest if HA is configured for it).
```

**Step 2: Pin python-socketio upper bound**

In manifest.json, change:
```json
"python-socketio[client]>=5.0"
```
to:
```json
"python-socketio[client]>=5.0,<6.0"
```

**Step 3: Fix sync/async callback mismatch**

In entity.py, replace line 31:
```python
self.async_write_ha_state()
```
with:
```python
self.schedule_update_ha_state()
```

**Step 4: Commit**
```
docs: add security section, pin dependency, fix callback (#1, #9, #7)
```

---

### Task 6: Version bump, changelog update, close issues

**Files:**
- Modify: `custom_components/maestro_mcz/manifest.json` (version to 1.2.0)
- Modify: `README.md` (update changelog)
- Modify: `CLAUDE.md` (update version)

**Step 1: Bump version to 1.2.0**

**Step 2: Update README changelog**

Add a 1.2.0 section above 1.1.1:
```markdown
### 1.2.0
- **feat:** Fan mode and power level presets on climate entity (#8)
- **feat:** Options flow to reconfigure serial/MAC after setup (#8)
- **feat:** Serial number and MAC address format validation in config flow (#4)
- **fix:** send_command raises HomeAssistantError instead of failing silently (#5)
- **fix:** Handshake errors now caught and logged (#5)
- **fix:** Use dict lookups instead of linear scans for commands and states (#6)
- **fix:** State change detection — only notify listeners when values change (#6)
- **fix:** Use schedule_update_ha_state for sync callbacks (#7)
- **docs:** Security considerations section in README (#1)
- **chore:** Pin python-socketio to <6.0 (#9)
```

**Step 3: Close issues on GitHub**

Close #1 with comment: "Documented as won't-fix (server limitation). Security section added to README."
Close #4, #5, #6, #8, #9 with fix references.

**Step 4: Commit**
```
chore: bump version to 1.2.0, update changelog
```

---

### Task 7: Tests and CI (#3)

**Files:**
- Modify: `.gitignore` (remove `tests/`)
- Create: `pyproject.toml`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_types.py`
- Create: `tests/test_controller.py`
- Create: `tests/test_climate.py`
- Create: `tests/test_config_flow.py`
- Create: `.github/workflows/ci.yml`

**Step 1: Remove tests/ from .gitignore**

Remove the `tests/` line from `.gitignore`.

**Step 2: Create pyproject.toml**

```toml
[project]
name = "ha-maestro-mcz"
version = "1.2.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
```

**Step 3: Create tests/conftest.py**

```python
"""Shared test fixtures."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.maestro_mcz.maestro.controller import MaestroController


@pytest.fixture
def controller():
    """Create a MaestroController with a mocked Socket.IO client."""
    with patch("custom_components.maestro_mcz.maestro.controller.socketio.AsyncClient") as mock_sio_class:
        mock_sio = AsyncMock()
        mock_sio.connected = False
        mock_sio_class.return_value = mock_sio
        ctrl = MaestroController("12345", "AA:BB:CC:DD:EE:FF")
        ctrl._sio = mock_sio
        yield ctrl
```

**Step 4: Create tests/test_types.py**

```python
"""Tests for protocol types and constants."""
from custom_components.maestro_mcz.maestro.types import (
    MAESTRO_COMMANDS,
    MAESTRO_COMMANDS_BY_NAME,
    MAESTRO_STOVE_STATES,
    MAESTRO_STOVE_STATES_BY_ID,
    MAESTRO_INFO,
)


def test_commands_by_name_has_all_commands():
    assert len(MAESTRO_COMMANDS_BY_NAME) == len(MAESTRO_COMMANDS)


def test_commands_by_name_lookup():
    cmd = MAESTRO_COMMANDS_BY_NAME["Temperature_Setpoint"]
    assert cmd.id == 42
    assert cmd.command_type == "temperature"


def test_stove_states_by_id_lookup():
    state = MAESTRO_STOVE_STATES_BY_ID[0]
    assert state.description == "Off"
    assert state.on_or_off == 0


def test_stove_states_by_id_power_levels():
    for level in range(1, 6):
        state = MAESTRO_STOVE_STATES_BY_ID[10 + level]
        assert state.description == f"Power {level}"
        assert state.on_or_off == 1


def test_info_active_set_point_is_temperature():
    info = MAESTRO_INFO[11]
    assert info.name == "Active_Set_Point"
    assert info.message_type == "temperature"
```

**Step 5: Create tests/test_controller.py**

```python
"""Tests for MaestroController."""
import pytest
from unittest.mock import AsyncMock, call

from custom_components.maestro_mcz.maestro.controller import MaestroController


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
        # Position 6 = Ambient_Temperature, 0x2B = 43 -> 21.5°C
        parts = ["01"] + ["00"] * 5 + ["2B"]
        controller._process_info_frame(parts)
        assert controller.state["Ambient_Temperature"] == 21.5

    def test_setpoint_conversion(self, controller):
        # Position 11 = Active_Set_Point, 0x2A = 42 -> 21.0°C
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
        callback = AsyncMock()
        controller.add_listener(callback)
        parts = ["01", "00"]
        controller._process_info_frame(parts)
        callback.assert_called_once()

    def test_listener_not_called_without_change(self, controller):
        # First call sets state
        controller._process_info_frame(["01", "00"])
        callback = AsyncMock()
        controller.add_listener(callback)
        # Second call with same data should not notify
        controller._process_info_frame(["01", "00"])
        callback.assert_not_called()


class TestSendCommand:
    @pytest.mark.asyncio
    async def test_temperature_encoding(self, controller):
        controller._sio.connected = True
        await controller.send_command("Temperature_Setpoint", 21.5)
        controller._sio.emit.assert_called_once()
        payload = controller._sio.emit.call_args[0][1]
        assert "|43" in payload["richiesta"]  # 21.5 * 2 = 43

    @pytest.mark.asyncio
    async def test_onoff40_on(self, controller):
        controller._sio.connected = True
        await controller.send_command("Power", 1)
        payload = controller._sio.emit.call_args[0][1]
        assert payload["richiesta"].endswith("|1")

    @pytest.mark.asyncio
    async def test_onoff40_off(self, controller):
        controller._sio.connected = True
        await controller.send_command("Power", 0)
        payload = controller._sio.emit.call_args[0][1]
        assert payload["richiesta"].endswith("|40")

    @pytest.mark.asyncio
    async def test_raises_when_disconnected(self, controller):
        controller._sio.connected = False
        with pytest.raises(Exception, match="not connected"):
            await controller.send_command("Power", 1)

    @pytest.mark.asyncio
    async def test_raises_for_unknown_command(self, controller):
        controller._sio.connected = True
        with pytest.raises(Exception, match="Unknown command"):
            await controller.send_command("NonExistent", 0)


class TestConnectGuard:
    @pytest.mark.asyncio
    async def test_duplicate_connect_prevented(self, controller):
        controller._running = True
        await controller.connect()
        # Should return immediately without calling sio.connect
        controller._sio.connect.assert_not_called()
```

**Step 6: Create tests/test_climate.py**

```python
"""Tests for climate entity HVAC action mapping."""
from unittest.mock import MagicMock

from custom_components.maestro_mcz.climate import (
    MaestroClimate,
    _HEATING_STATE_IDS,
    _COOLING_STATE_IDS,
)
from homeassistant.components.climate import HVACAction, HVACMode


def make_climate(state: dict) -> MaestroClimate:
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
```

**Step 7: Create tests/test_config_flow.py**

```python
"""Tests for config flow validation."""
import re


# Test the validation regex patterns directly (no HA dependency needed)
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

    def test_lowercase_normalized(self):
        # MAC should be uppercased before validation
        assert re.match(MAC_PATTERN, "AA:BB:CC:DD:EE:FF")
        assert not re.match(MAC_PATTERN, "aa:bb:cc:dd:ee:ff")

    def test_invalid_mac_short(self):
        assert not re.match(MAC_PATTERN, "AA:BB:CC")

    def test_invalid_mac_no_separator(self):
        assert not re.match(MAC_PATTERN, "AABBCCDDEEFF")
```

**Step 8: Create .github/workflows/ci.yml**

```yaml
name: CI

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pytest pytest-asyncio homeassistant python-socketio[client]
      - run: pytest tests/ -v

  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hacs/action@main
        with:
          category: integration

  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master
```

**Step 9: Run tests locally**

```bash
pip install pytest pytest-asyncio homeassistant python-socketio[client]
pytest tests/ -v
```

Expected: All tests pass.

**Step 10: Commit**
```
feat: add unit tests and CI pipeline (#3)
```

---

### Task 8: Final verification and push

**Step 1: Run full test suite**
```bash
pytest tests/ -v
```

**Step 2: Run ruff lint**
```bash
ruff check .
```

**Step 3: Verify all syntax**
```bash
python3 -c "import ast; [ast.parse(open(f).read()) for f in ['custom_components/maestro_mcz/__init__.py', 'custom_components/maestro_mcz/climate.py', 'custom_components/maestro_mcz/config_flow.py', 'custom_components/maestro_mcz/entity.py', 'custom_components/maestro_mcz/maestro/controller.py', 'custom_components/maestro_mcz/maestro/types.py']]"
```

**Step 4: Close remaining issues on GitHub**
```bash
gh issue close 1 --comment "Security section added to README. HTTP is a server-side limitation."
gh issue close 3 --comment "Tests and CI pipeline added in v1.2.0."
gh issue close 4 --comment "Fixed in v1.2.0."
gh issue close 5 --comment "Fixed in v1.2.0."
gh issue close 6 --comment "Fixed in v1.2.0."
gh issue close 8 --comment "Fixed in v1.2.0."
gh issue close 9 --comment "Fixed in v1.2.0."
```

**Step 5: Push**
```bash
git push origin master
```
