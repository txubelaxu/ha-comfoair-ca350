"""Binary sensor entities for the Zehnder ComfoAir 350 integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ComfoAirData
from .const import DOMAIN
from .entity import ComfoAirEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data: ComfoAirData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ComfoAirFilterFullBinarySensor(data)])


class ComfoAirFilterFullBinarySensor(ComfoAirEntity, BinarySensorEntity):
    _attr_translation_key = "filter_full"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, data: ComfoAirData) -> None:
        super().__init__(data, "filter_full")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get("filter_full")
