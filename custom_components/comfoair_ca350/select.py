"""Select entity to control the Zehnder ComfoAir 350 ventilation level."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ComfoAirData
from .const import DOMAIN, LABEL_TO_LEVEL, LEVEL_TO_LABEL
from .entity import ComfoAirEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data: ComfoAirData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ComfoAirLevelSelect(data)])


class ComfoAirLevelSelect(ComfoAirEntity, SelectEntity):
    _attr_translation_key = "ventilation_level"
    _attr_options = list(LABEL_TO_LEVEL)

    def __init__(self, data: ComfoAirData) -> None:
        super().__init__(data, "ventilation_level")

    @property
    def current_option(self) -> str | None:
        level = self.coordinator.data.get("ventilation_level")
        return LEVEL_TO_LABEL.get(level)

    async def async_select_option(self, option: str) -> None:
        level = LABEL_TO_LEVEL[option]
        await self.coordinator.async_set_ventilation_level(level)
