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
from homeassistant.const import PERCENTAGE, REVOLUTIONS_PER_MINUTE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ComfoAirData
from .const import DOMAIN
from .entity import ComfoAirEntity


@dataclass(frozen=True, kw_only=True)
class ComfoAirSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], object] = lambda data: None


TEMPERATURE_DESCRIPTIONS: tuple[ComfoAirSensorDescription, ...] = (
    ComfoAirSensorDescription(
        key="comfort_temp",
        translation_key="comfort_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.get("comfort_temp"),
    ),
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

    async_add_entities(entities)


class ComfoAirSensor(ComfoAirEntity, SensorEntity):
    entity_description: ComfoAirSensorDescription

    def __init__(self, data: ComfoAirData, description: ComfoAirSensorDescription) -> None:
        super().__init__(data, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator.data)
