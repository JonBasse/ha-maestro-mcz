# Maestro MCZ Home Assistant Integration

A Home Assistant integration for controlling MCZ stoves via the Maestro interface.

## Installation

### HACS (Recommended)
1. Ensure [HACS](https://hacs.xyz/) is installed.
2. Go to HACS -> Integrations.
3. Click the 3 dots in the top right corner and select "Custom repositories".
4. Add this repository URL (`https://github.com/JonBasse/ha-maestro-mcz`) with category "Integration".
5. Click "Download" on the "Maestro MCZ" card.
6. Restart Home Assistant.

### Manual
1. Copy the `custom_components/maestro_mcz` folder to your HA `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings** > **Devices & Services**.
2. Click **Add Integration** and search for **Maestro MCZ**.
3. Enter the IP address of your stove and the port (default 81).

## Features

- **Climate Control**: Set target temperature and HVAC mode (Heat/Off).
- **Sensors**: Monitor stove state, fume temperature, ambient temperature, and fan state.
- **Switches**: Control Silent Mode, Eco Mode, Sound Effects, and Chronostat.

## Credits

This integration is a fork and enhancement of the original work on MCZ Maestro connectivity. Special thanks to the original authors and the Home Assistant community.
