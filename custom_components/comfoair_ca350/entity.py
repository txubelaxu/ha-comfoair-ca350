"""Common base entity for the Zehnder ComfoAir 350 integration."""
from __future__ import annotations

import logging

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ComfoAirData
from .const import DOMAIN, MANUFACTURER
from .coordinator import ComfoAirCoordinator

_LOGGER = logging.getLogger(__name__)


class ComfoAirEntity(CoordinatorEntity[ComfoAirCoordinator]):
    """Base entity tying every platform entity to the same device."""

    _attr_has_entity_name = True

    @callback
    def _handle_coordinator_update(self) -> None:
        if self._key in ("fan_supply_pct", "fan_supply_rpm"):
            _LOGGER.warning(
                "DIAG _handle_coordinator_update fired key=%s entity_id=%s",
                self._key,
                self.entity_id,
            )
        super()._handle_coordinator_update()

    def __init__(
        self, data: ComfoAirData, key: str, coordinator: ComfoAirCoordinator | None = None
    ) -> None:
        super().__init__(coordinator or data.coordinator)
        self._key = key
        self._attr_unique_id = f"{data.coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, data.coordinator.entry.entry_id)},
            manufacturer=MANUFACTURER,
            name=data.firmware.get("name") or "ComfoAir 350",
            sw_version=f"{data.firmware.get('major')}.{data.firmware.get('minor')}",
        )
