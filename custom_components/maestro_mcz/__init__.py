"""The Maestro MCZ integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .maestro.controller import MaestroLocalController, MaestroCloudController

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR, Platform.SWITCH]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Maestro MCZ from a config entry."""
    
    hass.data.setdefault(DOMAIN, {})
    
    if entry.data.get("connection_type") == "cloud":
        controller = MaestroCloudController(entry.data["serial"], entry.data["mac"])
    else:
        # Default to local
        controller = MaestroLocalController(
            entry.data.get("host"), 
            entry.data.get("port", 81)
        )
        
    # Start connection in background task
    entry.async_create_background_task(hass, controller.connect(), "maestro_connect")
    
    hass.data[DOMAIN][entry.entry_id] = controller
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        controller: MaestroController = hass.data[DOMAIN][entry.entry_id]
        await controller.disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
