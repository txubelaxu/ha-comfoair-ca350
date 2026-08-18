"""Sensor entities for the Zehnder ComfoAir 350 integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ComfoAirData
from .const import DOMAIN
from .coordinator import ComfoAirCoordinator
from .entity import ComfoAirEntity


@dataclass(frozen=True, kw_only=True)
class ComfoAirSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], object] = lambda data: None


TEMPERATURE_DESCRIPTIONS: tuple[ComfoAirSensorDescription, ...] = (
    ComfoAirSensorDescription(
        key="temp_outside",
        translation_key="temp_outside",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.get("temp_outside"),
    ),
    ComfoAirSensorDescription(
        key="temp_supply",
        translation_key="temp_supply",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.get("temp_supply"),
    ),
    ComfoAirSensorDescription(
        key="temp_extract",
        translation_key="temp_extract",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.get("temp_extract"),
    ),
    ComfoAirSensorDescription(
        key="temp_exhaust",
        translation_key="temp_exhaust",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.get("temp_exhaust"),
    ),
)

OTHER_DESCRIPTIONS: tuple[ComfoAirSensorDescription, ...] = (
    ComfoAirSensorDescription(
        key="fan_supply_pct",
        translation_key="fan_supply_pct",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: data.get("fan_supply_pct"),
    ),
    ComfoAirSensorDescription(
        key="fan_extract_pct",
        translation_key="fan_extract_pct",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: data.get("fan_extract_pct"),
    ),
    ComfoAirSensorDescription(
        key="fan_supply_rpm",
        translation_key="fan_supply_rpm",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        value_fn=lambda data: data.get("fan_supply_rpm"),
    ),
    ComfoAirSensorDescription(
        key="fan_extract_rpm",
        translation_key="fan_extract_rpm",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        value_fn=lambda data: data.get("fan_extract_rpm"),
    ),
    ComfoAirSensorDescription(
        key="bypass_pct",
        translation_key="bypass_pct",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: data.get("bypass_pct"),
    ),
    ComfoAirSensorDescription(
        key="errors",
        translation_key="errors",
        value_fn=lambda data: ", ".join(data.get("errors", [])) or "none",
    ),
)

# Installation/configuration sensors, sourced from the slow-polled
# ComfoAirConfigCoordinator instead of the operational one.
CONFIG_DESCRIPTIONS: tuple[ComfoAirSensorDescription, ...] = (
    ComfoAirSensorDescription(
        key="unit_type",
        translation_key="unit_type",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=["left", "right"],
        value_fn=lambda data: data.get("unit_type"),
    ),
    ComfoAirSensorDescription(
        key="unit_size",
        translation_key="unit_size",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=["large", "small"],
        value_fn=lambda data: data.get("unit_size"),
    ),
    ComfoAirSensorDescription(
        key="enthalpy_present",
        translation_key="enthalpy_present",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=["absent", "present", "no_sensor", "unknown"],
        value_fn=lambda data: data.get("enthalpy_present"),
    ),
    ComfoAirSensorDescription(
        key="ewt_present",
        translation_key="ewt_present",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=["absent", "regulated", "unregulated", "unknown"],
        value_fn=lambda data: data.get("ewt_present"),
    ),
    ComfoAirSensorDescription(
        key="damper_status",
        translation_key="damper_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=["open", "closed", "unknown"],
        value_fn=lambda data: data.get("damper_status"),
    ),
    ComfoAirSensorDescription(
        key="frost_minutes",
        translation_key="frost_minutes",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda data: data.get("frost_minutes"),
    ),
    ComfoAirSensorDescription(
        key="rf_address",
        translation_key="rf_address",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("rf_address"),
    ),
    ComfoAirSensorDescription(
        key="rf_id",
        translation_key="rf_id",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("rf_id"),
    ),
    ComfoAirSensorDescription(
        key="analog_priority",
        translation_key="analog_priority",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=["analog_inputs", "schedule"],
        value_fn=lambda data: data.get("analog_priority"),
    ),
) + tuple(
    ComfoAirSensorDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=(lambda k: lambda data: data.get(k))(key),
    )
    for key in (
        "hours_away",
        "hours_low",
        "hours_medium",
        "hours_high",
        "hours_frost_protection",
        "hours_preheater",
        "hours_bypass_open",
        "hours_filter",
    )
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data: ComfoAirData = hass.data[DOMAIN][entry.entry_id]

    entities: list[ComfoAirSensor] = list(
        ComfoAirSensor(data, description) for description in OTHER_DESCRIPTIONS
    )

    # Only expose temperature probes the unit actually reported on first poll.
    for description in TEMPERATURE_DESCRIPTIONS:
        if description.value_fn(data.coordinator.data) is not None:
            entities.append(ComfoAirSensor(data, description))

    entities.extend(
        ComfoAirSensor(data, description, coordinator=data.config_coordinator)
        for description in CONFIG_DESCRIPTIONS
    )

    async_add_entities(entities)


class ComfoAirSensor(ComfoAirEntity, SensorEntity):
    entity_description: ComfoAirSensorDescription

    def __init__(
        self,
        data: ComfoAirData,
        description: ComfoAirSensorDescription,
        coordinator: ComfoAirCoordinator | None = None,
    ) -> None:
        super().__init__(data, description.key, coordinator=coordinator)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)
