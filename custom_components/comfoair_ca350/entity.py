"""Common base entity for the Zehnder ComfoAir 350 integration."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComfoAirData
from .const import DOMAIN, MANUFACTURER
from .coordinator import ComfoAirCoordinator


class ComfoAirEntity(CoordinatorEntity[ComfoAirCoordinator]):
    """Base entity tying every platform entity to the same device."""

    _attr_has_entity_name = True

    def __init__(self, data: ComfoAirData, key: str) -> None:
        super().__init__(data.coordinator)
        self._key = key
        self._attr_unique_id = f"{data.coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, data.coordinator.entry.entry_id)},
            manufacturer=MANUFACTURER,
            name=data.firmware.get("name") or "ComfoAir 350",
            sw_version=f"{data.firmware.get('major')}.{data.firmware.get('minor')}",
        )
