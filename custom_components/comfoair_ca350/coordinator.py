"""DataUpdateCoordinator for the Zehnder ComfoAir 350 integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL
from .protocol import ComfoAirClient, ComfoAirError

_LOGGER = logging.getLogger(__name__)


class ComfoAirCoordinator(DataUpdateCoordinator[dict]):
    """Polls the ComfoAir unit and hands out the latest values."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: ComfoAirClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            return await self.hass.async_add_executor_job(self.client.poll_all)
        except ComfoAirError as err:
            raise UpdateFailed(f"Error comunicando con la ComfoAir: {err}") from err

    async def async_set_ventilation_level(self, level: int) -> None:
        await self.hass.async_add_executor_job(self.client.set_ventilation_level, level)
        await self.async_request_refresh()
