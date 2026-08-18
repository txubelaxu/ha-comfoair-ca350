"""Binary sensor entities for the Zehnder ComfoAir 350 integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ComfoAirData
from .const import DOMAIN
from .entity import ComfoAirEntity


@dataclass(frozen=True, kw_only=True)
class ComfoAirBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict], object] = lambda data: None


# Installed-hardware flags from the wall control's install menu. Sourced from
# the slow-polled ComfoAirConfigCoordinator.
CONFIG_DESCRIPTIONS: tuple[ComfoAirBinarySensorDescription, ...] = (
    ComfoAirBinarySensorDescription(
        key="preheater_present",
        translation_key="preheater_present",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("preheater_present"),
    ),
    ComfoAirBinarySensorDescription(
        key="bypass_present",
        translation_key="bypass_present",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("bypass_present"),
    ),
    ComfoAirBinarySensorDescription(
        key="option_fireplace",
        translation_key="option_fireplace",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("option_fireplace"),
    ),
    ComfoAirBinarySensorDescription(
        key="option_kitchen_hood",
        translation_key="option_kitchen_hood",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("option_kitchen_hood"),
    ),
    ComfoAirBinarySensorDescription(
        key="option_postheater",
        translation_key="option_postheater",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("option_postheater"),
    ),
    ComfoAirBinarySensorDescription(
        key="frost_protection_active",
        translation_key="frost_protection_active",
        device_class=BinarySensorDeviceClass.COLD,
        value_fn=lambda data: data.get("frost_protection_active"),
    ),
    ComfoAirBinarySensorDescription(
        key="preheater_active",
        translation_key="preheater_active",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda data: data.get("preheater_active"),
    ),
)

# Analog/RF input channels. "Present" is always shown so it's obvious at a
# glance which ones are wired; the regulating-mode / inverted flags are only
# meaningful (and only created) for channels that are actually present.
_ANALOG_CHANNELS = ("analog1", "analog2", "analog3", "analog4", "rf")

ANALOG_PRESENCE_DESCRIPTIONS: tuple[ComfoAirBinarySensorDescription, ...] = tuple(
    ComfoAirBinarySensorDescription(
        key=f"{name}_present",
        translation_key=f"{name}_present",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=(lambda k: lambda data: data.get(k))(f"{name}_present"),
    )
    for name in _ANALOG_CHANNELS
)


def _analog_flag_descriptions(name: str) -> tuple[ComfoAirBinarySensorDescription, ...]:
    return (
        ComfoAirBinarySensorDescription(
            key=f"{name}_regulating",
            translation_key=f"{name}_regulating",
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=(lambda k: lambda data: data.get(k))(f"{name}_regulating"),
        ),
        ComfoAirBinarySensorDescription(
            key=f"{name}_inverted",
            translation_key=f"{name}_inverted",
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=(lambda k: lambda data: data.get(k))(f"{name}_inverted"),
        ),
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data: ComfoAirData = hass.data[DOMAIN][entry.entry_id]
    entities: list = [ComfoAirFilterFullBinarySensor(data), ComfoAirSummerModeBinarySensor(data)]
    entities.extend(
        ComfoAirConfigBinarySensor(data, description) for description in CONFIG_DESCRIPTIONS
    )
    entities.extend(
        ComfoAirConfigBinarySensor(data, description)
        for description in ANALOG_PRESENCE_DESCRIPTIONS
    )
    for name in _ANALOG_CHANNELS:
        if data.config_coordinator.data.get(f"{name}_present"):
            entities.extend(
                ComfoAirConfigBinarySensor(data, description)
                for description in _analog_flag_descriptions(name)
            )
    async_add_entities(entities)


class ComfoAirFilterFullBinarySensor(ComfoAirEntity, BinarySensorEntity):
    _attr_translation_key = "filter_full"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, data: ComfoAirData) -> None:
        super().__init__(data, "filter_full")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get("filter_full")


class ComfoAirSummerModeBinarySensor(ComfoAirEntity, BinarySensorEntity):
    _attr_translation_key = "summer_mode"

    def __init__(self, data: ComfoAirData) -> None:
        super().__init__(data, "summer_mode")

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get("summer_mode")


class ComfoAirConfigBinarySensor(ComfoAirEntity, BinarySensorEntity):
    entity_description: ComfoAirBinarySensorDescription

    def __init__(self, data: ComfoAirData, description: ComfoAirBinarySensorDescription) -> None:
        super().__init__(data, description.key, coordinator=data.config_coordinator)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)
