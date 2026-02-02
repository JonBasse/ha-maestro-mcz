# Maestro MCZ for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

A Home Assistant integration for **MCZ Maestro** pellet stoves using the MCZ Cloud.

## Prerequisites

- A working **MCZ Maestro** app account
- Your stove's **Serial Number** -- found on the sticker on the back of the stove, or in the MCZ Maestro app under stove settings
- Your stove's **MAC Address** -- found in the MCZ Maestro app under stove settings, or on the stove's Wi-Fi module sticker

## Features

- **Climate control**: Turn your stove on/off and set the target temperature
- **Sensors**: Real-time monitoring of ambient temperature, fume temperature, fan state, and stove state
- **Switches**: Toggle silent mode, eco mode, sound effects, and chronostat
- **Cloud-based**: Connects to `app.mcz.it` via Socket.IO -- no local network configuration required
- **Real-time updates**: WebSocket push notifications for instant state feedback

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| Climate | `climate` | Main stove control (on/off, target temperature, HVAC action) |
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
4. Enter your stove's **Serial Number** and **MAC Address**.
5. The integration will validate the connection to MCZ Cloud before completing setup.

## Troubleshooting

- **"Unable to connect to MCZ Cloud"** during setup: Verify that your serial number and MAC address are correct. Ensure the MCZ Maestro app can connect to your stove.
- **Entity shows "unavailable"**: The cloud connection may have dropped. The integration will automatically reconnect.
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

## Support

If you encounter issues, please open an issue in this repository.
When reporting bugs, please enable debug logging and provide the log output.

---
*Not affiliated with MCZ Group.*
