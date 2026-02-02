"""The Maestro MCZ integration."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .maestro.controller import MaestroController

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Maestro MCZ from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    controller = MaestroController(entry.data["serial"], entry.data["mac"])

    # Attempt initial connection; raise ConfigEntryNotReady on failure
    try:
        async with asyncio.timeout(15):
            await controller.connect_once()
    except Exception as err:
        await controller.disconnect()
        raise ConfigEntryNotReady(
            f"Unable to connect to MCZ Cloud for serial {entry.data['serial']}"
        ) from err

    hass.data[DOMAIN][entry.entry_id] = controller

    # Start persistent reconnection loop in background
    entry.async_create_background_task(hass, controller.connect(), "maestro_connect")

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        controller: MaestroController = hass.data[DOMAIN][entry.entry_id]
        await controller.disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
