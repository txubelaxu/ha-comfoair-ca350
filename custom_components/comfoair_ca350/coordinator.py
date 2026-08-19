"""DataUpdateCoordinators for the Zehnder ComfoAir 350 integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL
from .protocol import ComfoAirClient, ComfoAirError

_LOGGER = logging.getLogger(__name__)

# Installation/configuration values (delays, install status, EWT setpoints...)
# only change when someone edits them on the wall control or via this
# integration - polling them every 30s like live sensor data would just add
# needless RS232 traffic and retry risk on an already timing-sensitive link.
CONFIG_UPDATE_INTERVAL = timedelta(minutes=5)


class ComfoAirCoordinator(DataUpdateCoordinator[dict]):
    """Polls fast-changing operational data (temperatures, fans, level...)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: ComfoAirClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_operational",
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            async with self.client.async_lock:
                return await self.hass.async_add_executor_job(self.client.poll_all, self.data)
        except ComfoAirError as err:
            raise UpdateFailed(f"Error comunicando con la ComfoAir: {err}") from err

    async def async_set_ventilation_level(self, level: int) -> None:
        await self.hass.async_add_executor_job(self.client.set_ventilation_level, level)
        await self.async_request_refresh()

    async def async_set_level_percentages(self, **overrides: int) -> None:
        await self.hass.async_add_executor_job(
            lambda: self.client.set_level_percentages(**overrides)
        )
        await self.async_request_refresh()

    async def async_set_comfort_temp(self, celsius: float) -> None:
        await self.hass.async_add_executor_job(self.client.set_comfort_temp, celsius)
        await self.async_request_refresh()

    async def async_reset_filter(self) -> None:
        await self.hass.async_add_executor_job(self.client.reset_filter)
        await self.async_request_refresh()

    async def async_reset_faults(self) -> None:
        await self.hass.async_add_executor_job(self.client.reset_faults)
        await self.async_request_refresh()

    async def async_start_selftest(self) -> None:
        await self.hass.async_add_executor_job(self.client.start_selftest)
        await self.async_request_refresh()


class ComfoAirConfigCoordinator(DataUpdateCoordinator[dict]):
    """Polls slow-changing installation/configuration data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: ComfoAirClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_config",
            update_interval=CONFIG_UPDATE_INTERVAL,
        )
        self.entry = entry
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            async with self.client.async_lock:
                return await self.hass.async_add_executor_job(self.client.poll_config, self.data)
        except ComfoAirError as err:
            raise UpdateFailed(f"Error comunicando con la ComfoAir: {err}") from err

    async def async_set_delays(self, **overrides: int) -> None:
        await self.hass.async_add_executor_job(lambda: self.client.set_delays(**overrides))
        await self.async_request_refresh()

    async def async_set_ewt_postheater(self, **overrides: int) -> None:
        await self.hass.async_add_executor_job(
            lambda: self.client.set_ewt_postheater(**overrides)
        )
        await self.async_request_refresh()

    async def async_set_analog_values(self, **overrides: int) -> None:
        await self.hass.async_add_executor_job(
            lambda: self.client.set_analog_values(**overrides)
        )
        await self.async_request_refresh()
