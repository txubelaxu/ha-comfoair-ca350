"""The Zehnder ComfoAir 350 integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_PORT, DOMAIN
from .coordinator import ComfoAirConfigCoordinator, ComfoAirCoordinator
from .protocol import ComfoAirClient, ComfoAirError

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
]


@dataclass
class ComfoAirData:
    client: ComfoAirClient
    coordinator: ComfoAirCoordinator
    config_coordinator: ComfoAirConfigCoordinator
    firmware: dict


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    port = entry.data[CONF_PORT]
    client = ComfoAirClient(port)

    def _connect_and_probe() -> dict:
        client.connect()
        return client.get_firmware()

    try:
        firmware = await hass.async_add_executor_job(_connect_and_probe)
    except ComfoAirError as err:
        client.close()
        raise ConfigEntryNotReady(f"No se pudo conectar con la ComfoAir en {port}: {err}") from err
    except Exception:
        client.close()
        raise

    coordinator = ComfoAirCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    config_coordinator = ComfoAirConfigCoordinator(hass, entry, client)
    await config_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ComfoAirData(
        client=client,
        coordinator=coordinator,
        config_coordinator=config_coordinator,
        firmware=firmware,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data: ComfoAirData = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(data.client.close)
    return unload_ok
