"""Config flow for Maestro MCZ integration."""
import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN
from .maestro.controller import MaestroController

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("serial"): str,
        vol.Required("mac"): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Maestro MCZ."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - Connection setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            serial = user_input["serial"].strip()
            mac = user_input["mac"].strip()

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

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
