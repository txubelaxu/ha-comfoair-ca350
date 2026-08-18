"""Config flow for the Zehnder ComfoAir 350 integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_PORT, DEFAULT_PORT, DOMAIN
from .protocol import ComfoAirClient, ComfoAirError

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema({vol.Required(CONF_PORT, default=DEFAULT_PORT): str})


def _probe_port(port: str) -> dict:
    client = ComfoAirClient(port)
    try:
        client.connect()
        return client.get_firmware()
    finally:
        client.close()


class ComfoAirConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Zehnder ComfoAir 350."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            port = user_input[CONF_PORT]
            await self.async_set_unique_id(port)
            self._abort_if_unique_id_configured()

            try:
                firmware = await self.hass.async_add_executor_job(_probe_port, port)
            except ComfoAirError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Error inesperado al conectar con la ComfoAir")
                errors["base"] = "unknown"
            else:
                name = firmware.get("name") or "Zehnder ComfoAir 350"
                return self.async_create_entry(title=name, data={CONF_PORT: port})

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
