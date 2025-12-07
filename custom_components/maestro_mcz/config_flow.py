"""Config flow for Maestro MCZ integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .maestro.controller import MaestroController

_LOGGER = logging.getLogger(__name__)

CONN_LOCAL = "Local"
CONN_CLOUD = "Cloud"

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Maestro MCZ."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - Connection setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
             return self.async_create_entry(
                 title=f"Maestro Cloud ({user_input['serial']})", 
                 data={
                     "connection_type": "cloud",
                     "serial": user_input['serial'],
                     "mac": user_input['mac']
                 }
            )

        schema = vol.Schema(
            {
                vol.Required("serial", description="Serial Number"): str,
                vol.Required("mac", description="MAC Address"): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
