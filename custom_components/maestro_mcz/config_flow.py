"""Config flow for Maestro MCZ integration."""
import asyncio
import logging
import re
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

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow handler."""
        return MaestroOptionsFlow(config_entry)


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
                    vol.Required(
                        "serial",
                        default=self._config_entry.data.get("serial", ""),
                    ): str,
                    vol.Required(
                        "mac",
                        default=self._config_entry.data.get("mac", ""),
                    ): str,
                }
            ),
            errors=errors,
        )
