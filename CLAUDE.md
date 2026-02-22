# CLAUDE.md — ha-maestro-mcz

## Project
Home Assistant custom integration for **MCZ Maestro pellet stoves** via cloud Socket.IO.
Distributed through HACS. Version 1.1.1. Domain: `maestro_mcz`.

## Structure
```
custom_components/maestro_mcz/
├── __init__.py          # Entry point: setup, teardown, background connection
├── config_flow.py       # Config UI: serial + MAC validation
├── const.py             # DOMAIN constant
├── entity.py            # MaestroEntity base class (DeviceInfo, availability, listeners)
├── climate.py           # Climate entity (HEAT mode, 10-35°C)
├── sensor.py            # 4 sensors: Stove_State_Desc, Fume/Ambient temp, Fan_State
├── switch.py            # 4 switches: Silent_Mode, Eco_Mode, Sound_Effects, Chronostat
├── manifest.json        # Integration metadata
├── strings.json         # UI strings
├── translations/en.json # English translations
└── maestro/
    ├── controller.py    # MaestroController: Socket.IO client, state, commands
    └── types.py         # Protocol: commands, stove states, info frame mapping
```

## Architecture
- **MaestroController** connects to `http://app.mcz.it:9000` via Socket.IO
- Authenticates with serial + MAC, identifies as `"Android-App"`
- Receives state via `"rispondo"` events (pipe-delimited hex), sends commands via `"chiedo"` events
- Observer pattern: entities register as listeners, controller notifies on state change
- Persistent background connection loop with 10-second auto-reconnect
- `ConfigEntryNotReady` raised on setup failure (15s timeout)

## Protocol
- **Inbound messages:** `01|<hex>|<hex>|...` — position-mapped fields per `MAESTRO_INFO`
- **Temperatures:** stored as 2× value (21.5°C = hex 0x2B = 43 → 43/2 = 21.5)
- **Commands:** `C|WriteParametri|<cmd_id>|<value>` — types: `temperature` (×2), `onoff` (0/1), `onoff40` (0→40, 1→1)
- **Stove states:** 0=Off, 1-15=Operating, 31=On, 40-49=Post-op, 50-69=Errors

## Development Guidelines
- **Min HA version:** 2025.1.0
- **Only dependency:** `python-socketio[client]>=5.0`
- **Platforms:** Climate, Sensor, Switch
- **Unique ID format:** `{DOMAIN}_{serial}_{entity_type}`
- **Device identity:** manufacturer="MCZ", model="Maestro", name="Maestro Stove"
- Keep all protocol constants in `maestro/types.py`
- Keep controller logic in `maestro/controller.py`, entity logic in platform files
- Follow Home Assistant integration patterns (async_setup_entry, config_flow, etc.)

## Commit Style
- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`
- Keep messages concise (1-2 sentences)
