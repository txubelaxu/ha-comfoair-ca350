"""Number entity to read/set the Zehnder ComfoAir 350 comfort temperature."""
from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ComfoAirData
from .const import DOMAIN
from .entity import ComfoAirEntity
from .protocol import COMFORT_TEMP_MAX, COMFORT_TEMP_MIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data: ComfoAirData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ComfoAirComfortTempNumber(data)])


class ComfoAirComfortTempNumber(ComfoAirEntity, NumberEntity):
    _attr_translation_key = "comfort_temp"
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = COMFORT_TEMP_MIN
    _attr_native_max_value = COMFORT_TEMP_MAX
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX

    def __init__(self, data: ComfoAirData) -> None:
        super().__init__(data, "comfort_temp")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.get("comfort_temp")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_comfort_temp(value)
