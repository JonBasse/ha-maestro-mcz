# Maestro MCZ for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

A Home Assistant integration for **MCZ Maestro** pellet stoves using the MCZ Cloud.

## Prerequisites

- A working **MCZ Maestro** app account
- Your stove's **Serial Number** -- found on the sticker on the back of the stove, or in the MCZ Maestro app under stove settings
- Your stove's **MAC Address** -- found in the MCZ Maestro app under stove settings, or on the stove's Wi-Fi module sticker

## Features

- **Climate control**: Turn your stove on/off, set the target temperature, fan mode, and power level presets
- **Sensors**: Real-time monitoring of ambient temperature, fume temperature, fan state, and stove state
- **Switches**: Toggle silent mode, eco mode, sound effects, and chronostat
- **Cloud-based**: Connects to `app.mcz.it` via Socket.IO -- no local network configuration required
- **Real-time updates**: WebSocket push notifications for instant state feedback
- **Automatic reconnection**: Exponential backoff with dead-connection detection via engineio ping/pong
- **Periodic polling**: Requests fresh data every 120s to keep sensors current even without cloud push

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| Climate | `climate` | Main stove control (on/off, target temperature, fan mode, power level presets, HVAC action) |
| Stove State | `sensor` | Current stove state description (e.g. "Off", "Power 3", "Cooling") |
| Ambient Temperature | `sensor` | Room temperature reported by the stove |
| Fume Temperature | `sensor` | Exhaust fume temperature |
| Fan State | `sensor` | Current fan level |
| Silent Mode | `switch` | Toggle silent/quiet operation |
| Eco Mode | `switch` | Toggle eco mode |
| Sound Effects | `switch` | Toggle stove sound effects |
| Chronostat | `switch` | Toggle the built-in chronostat/scheduler |

## Compatibility

- **Minimum Home Assistant version**: 2025.1.0
- **Tested with**: MCZ Maestro-equipped pellet stoves using cloud connection

## Installation via HACS

1. Open **HACS** in Home Assistant.
2. Go to **Integrations** > **Three dots (top right)** > **Custom repositories**.
3. Add `https://github.com/JonBasse/ha-maestro-mcz` with category **Integration**.
4. Click **Add** and then search for "Maestro MCZ".
5. Click **Download**.
6. **Restart Home Assistant**.

## Configuration

1. Go to **Settings** > **Devices & Services**.
2. Click **Add Integration**.
3. Search for **Maestro MCZ**.
4. Enter your stove's **Serial Number** (digits only) and **MAC Address** (format: `AA:BB:CC:DD:EE:FF`).
5. The integration will validate the format and test the connection to MCZ Cloud before completing setup.

To reconfigure your serial number or MAC address after setup, go to the integration's **Options** (gear icon).

## Troubleshooting

- **"Invalid serial number"** during setup: The serial number must contain only digits.
- **"Invalid MAC address"** during setup: The MAC address must be in `AA:BB:CC:DD:EE:FF` or `AA-BB-CC-DD-EE-FF` format (hex characters only).
- **"Unable to connect to MCZ Cloud"** during setup: Verify that your serial number and MAC address are correct. Ensure the MCZ Maestro app can connect to your stove.
- **Entity shows "unavailable"**: The cloud connection may have dropped. The integration will automatically reconnect. Last known values are preserved during brief reconnect cycles.
- **Enable debug logging** for detailed diagnostics:

```yaml
logger:
  default: info
  logs:
    custom_components.maestro_mcz: debug
```

## Credits

This integration stands on the shoulders of giants. Thanks to the community for reverse-engineering the protocol:

- **[pipolaq/maestro](https://github.com/pipolaq/maestro)**: Socket.IO protocol analysis and Python implementation reference
- **[hackximus/MCZ-Maestro-API](https://github.com/hackximus/MCZ-Maestro-API)**: Initial research into the Maestro API
- **Chibald** and **Anthony L.** for their pioneering work in the MCZ community

## Security Considerations

- **Unencrypted connection**: The MCZ cloud endpoint (`app.mcz.it:9000`) uses plain HTTP. This is a limitation of the MCZ cloud server — the official MCZ Maestro app also uses HTTP. Serial numbers and MAC addresses are transmitted in cleartext.
- **Credential model**: Access is controlled by serial number and MAC address only (no username/password). Anyone with these values can control the stove.
- **Config storage**: Credentials are stored in Home Assistant's config entries (standard HA behavior, encrypted at rest if HA is configured for it).

## Changelog

### 1.4.0
- **fix:** Remove 600s artificial timeout that killed healthy Socket.IO connections every 10 minutes
- **fix:** Disable socketio built-in reconnection to prevent conflict with the controller's own reconnection loop
- **fix:** Preserve state on disconnect — entities keep last known values during brief reconnect cycles instead of flashing "unavailable"
- **feat:** Periodic `GetInfo` polling every 120s keeps sensor data fresh when the cloud doesn't push updates
- **feat:** Staleness detection warns in logs if no data received in 360s despite active polling
- **feat:** Connection lifecycle events (connect, join, disconnect, reconnect) now logged at INFO level
- **chore:** Improved error tracing with full stack traces in message processing

### 1.3.3
- **chore:** Bump version for HACS submission
- **chore:** Add MIT license (required for HACS)

### 1.3.1
- **fix:** Use `_connected` flag in `send_command` guard to prevent race condition
- **chore:** CI and lint fixes

### 1.3.0
- **fix:** Use Power register (reg 34) instead of Active_Mode for stove on/off — fixes HVAC mode control
- **fix:** Temperature rounding uses `round()` instead of `int()` truncation, with 0.5°C step constraint
- **fix:** Socket leak in config flow — `disconnect()` now called on connection failure
- **fix:** Reconnect loop properly disconnects before retry and re-raises `CancelledError`
- **fix:** Listener iteration uses snapshot to prevent corruption during notification
- **fix:** Guard `fan_mode` and `preset_mode` against invalid input (crash prevention)
- **fix:** Exponential backoff on reconnection (10s → 300s cap), resets on success
- **fix:** `sio.wait()` timeout (10 min) prevents silent hangs on half-open connections
- **fix:** Busy-loop fix when reconnection loop starts with an existing connection
- **fix:** Clear stale state on disconnect — entities get fresh data on reconnect
- **fix:** Platform setup before background task — entities register listeners before data arrives
- **fix:** Options flow validates connection with new credentials before persisting changes
- **fix:** Modernize OptionsFlow to use base class `config_entry` property
- **fix:** Add `super()` calls in entity lifecycle and use `async_write_ha_state()`
- **test:** Test suite expanded from 66 to 119 tests — new coverage for entity, sensor, switch, climate, and controller message handling
- **chore:** Pin CI GitHub Actions to SHA for supply chain safety

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

### 1.1.1
- **fix:** Target temperature now correctly reads from the stove's active setpoint (was always showing as unavailable)
- **fix:** Connection loop now prevents duplicate concurrent loops on reload

### 1.1.0
- Production readiness improvements: validation, unique IDs, error handling

### 1.0.0
- Initial release with cloud support via Socket.IO

## Support

If you encounter issues, please open an issue in this repository.
When reporting bugs, please enable debug logging and provide the log output.

---
*Not affiliated with MCZ Group.*
