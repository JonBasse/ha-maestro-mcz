# Maestro MCZ for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

A robust **Home Assistant** integration for **MCZ Maestro** pellet stoves. 
This integration utilizes the **MCZ Cloud** to reliably control your stove without requiring complex local network configurations or firewall adjustments.

## Features

- 🔥 **Full Control**: Turn your stove On/Off, set Target Temperature.
- 🌡️ **Sensors**: Real-time monitoring of Ambient Temperature, Fume Temperature, Fan State, and more.
- ⚡ **Instant Updates**: Uses WebSocket technology for real-time state feedback.
- ☁️ **Cloud Based**: Connects directly to `app.mcz.it` - no local IP headaches!
- ⚙️ **Easy Configuration**: Just provide your Serial Number and MAC Address.

## Installation via HACS

1.  Open **HACS** in Home Assistant.
2.  Go to **Integrations** > **Three dots (top right)** > **Custom repositories**.
3.  Add `https://github.com/JonBasse/ha-maestro-mcz` with category **Integration**.
4.  Click **Add** and then search for "Maestro MCZ".
5.  Click **Download**.
6.  **Restart Home Assistant**.

## Configuration

1.  Go to **Settings** > **Devices & Services**.
2.  Click **Add Integration**.
3.  Search for **Maestro MCZ**.
4.  Enter your stove's details:
    -   **Serial Number**: (e.g., `1234567890123`) - Found on the sticker on the back or in your MCZ App."
    -   **MAC Address**: (e.g., `AA:BB:CC:DD:EE:FF`) - Found in your MCZ App or sticker.

## Credits

This integration stands on the shoulders of giants. A massive thank you to the community for reverse-engineering the protocol:

-   **[pipolaq/maestro](https://github.com/pipolaq/maestro)**: For the Socket.IO protocol analysis and Python implementation reference.
-   **[hackximus/MCZ-Maestro-API](https://github.com/hackximus/MCZ-Maestro-API)**: For initial research into the Maestro API.
-   **Chibald** and **Anthony L.** for their pioneering work in the MCZ community.

## Support

If you encounter issues, please open an issue in this repository. 
When reporting bugs, please enable "Enable Debug Logging" in the integration settings and provide the log output.

You can also enable debug logging manually in your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.maestro_mcz: debug
```

---
*Not affiliated with MCZ Group.*
