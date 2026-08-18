"""Button entity to reset the Zehnder ComfoAir 350 filter runtime counter."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ComfoAirData
from .const import DOMAIN
from .entity import ComfoAirEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data: ComfoAirData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ComfoAirResetFilterButton(data)])


class ComfoAirResetFilterButton(ComfoAirEntity, ButtonEntity):
    entity_description = ButtonEntityDescription(
        key="reset_filter",
        translation_key="reset_filter",
        entity_category=EntityCategory.CONFIG,
    )

    def __init__(self, data: ComfoAirData) -> None:
        super().__init__(data, "reset_filter")

    async def async_press(self) -> None:
        await self.coordinator.async_reset_filter()
