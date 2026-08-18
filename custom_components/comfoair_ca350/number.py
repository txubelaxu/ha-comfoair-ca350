"""Number entities to read/set writable Zehnder ComfoAir 350 parameters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ComfoAirData
from .const import DOMAIN
from .coordinator import ComfoAirConfigCoordinator, ComfoAirCoordinator
from .entity import ComfoAirEntity
from .protocol import COMFORT_TEMP_MAX, COMFORT_TEMP_MIN


@dataclass(frozen=True, kw_only=True)
class ComfoAirNumberDescription:
    key: str
    translation_key: str
    min_value: float
    max_value: float
    step: float = 1
    unit: str | None = PERCENTAGE
    entity_category: EntityCategory | None = EntityCategory.CONFIG
    on_config_coordinator: bool = False
    setter_method: str = "async_set_level_percentages"
    value_fn: Callable[[dict], object] = lambda data: None


LEVEL_PERCENTAGE_DESCRIPTIONS: tuple[ComfoAirNumberDescription, ...] = tuple(
    ComfoAirNumberDescription(
        key=key,
        translation_key=key,
        min_value=0,
        max_value=100,
        setter_method="async_set_level_percentages",
        value_fn=(lambda k: lambda data: data.get(k))(key),
    )
    for key in (
        "extract_pct_away",
        "extract_pct_low",
        "extract_pct_medium",
        "extract_pct_high",
        "supply_pct_away",
        "supply_pct_low",
        "supply_pct_medium",
        "supply_pct_high",
    )
)

_MINUTE_DELAY_KEYS = (
    "bathroom_switch_on_delay",
    "bathroom_switch_off_delay",
    "l1_off_delay",
    "boost_duration",
    "rf_high_time_short",
    "rf_high_time_long",
    "kitchen_hood_off_delay",
)

DELAY_DESCRIPTIONS: tuple[ComfoAirNumberDescription, ...] = tuple(
    ComfoAirNumberDescription(
        key=key,
        translation_key=key,
        min_value=0,
        max_value=255,
        unit=UnitOfTime.MINUTES,
        on_config_coordinator=True,
        setter_method="async_set_delays",
        value_fn=(lambda k: lambda data: data.get(k))(key),
    )
    for key in _MINUTE_DELAY_KEYS
) + (
    ComfoAirNumberDescription(
        key="filter_weeks",
        translation_key="filter_weeks",
        min_value=0,
        max_value=52,
        unit=UnitOfTime.WEEKS,
        on_config_coordinator=True,
        setter_method="async_set_delays",
        value_fn=lambda data: data.get("filter_weeks"),
    ),
)

# (key, translation_key, min, max, unit) - all gated on the matching
# temperature probe being present, and applied against the EWT/postheater
# read-modify-write block.
_EWT_POSTHEATER_NUMBERS = (
    ("ewt_temp_low", "temp_ewt", 0, 40, UnitOfTemperature.CELSIUS),
    ("ewt_temp_high", "temp_ewt", 0, 40, UnitOfTemperature.CELSIUS),
    ("ewt_speed_pct", "temp_ewt", 0, 100, PERCENTAGE),
    ("kitchen_hood_speed_pct", "temp_kitchenhood", 0, 100, PERCENTAGE),
    ("postheater_target_temp", "temp_postheater", 0, 40, UnitOfTemperature.CELSIUS),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data: ComfoAirData = hass.data[DOMAIN][entry.entry_id]

    entities: list = [ComfoAirComfortTempNumber(data)]
    entities.extend(ComfoAirNumber(data, d) for d in LEVEL_PERCENTAGE_DESCRIPTIONS)
    entities.extend(ComfoAirNumber(data, d) for d in DELAY_DESCRIPTIONS)

    for key, presence_key, min_value, max_value, unit in _EWT_POSTHEATER_NUMBERS:
        if presence_key not in data.coordinator.data:
            continue
        entities.append(
            ComfoAirNumber(
                data,
                ComfoAirNumberDescription(
                    key=key,
                    translation_key=key,
                    min_value=min_value,
                    max_value=max_value,
                    unit=unit,
                    on_config_coordinator=True,
                    setter_method="async_set_ewt_postheater",
                    value_fn=(lambda k: lambda data: data.get(k))(key),
                ),
            )
        )

    async_add_entities(entities)


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


class ComfoAirNumber(ComfoAirEntity, NumberEntity):
    """Generic number entity backed by a read-modify-write protocol block."""

    entity_description: ComfoAirNumberDescription
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, data: ComfoAirData, description: ComfoAirNumberDescription) -> None:
        coordinator: ComfoAirCoordinator | ComfoAirConfigCoordinator = (
            data.config_coordinator if description.on_config_coordinator else data.coordinator
        )
        super().__init__(data, description.key, coordinator=coordinator)
        self.entity_description = description
        self._attr_translation_key = description.translation_key
        self._attr_native_unit_of_measurement = description.unit
        self._attr_native_min_value = description.min_value
        self._attr_native_max_value = description.max_value
        self._attr_native_step = description.step
        self._attr_entity_category = description.entity_category

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        method = getattr(self.coordinator, self.entity_description.setter_method)
        await method(**{self.entity_description.key: round(value)})
