"""Sensor for Econet300."""
from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntityDescription,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common_functions import camel_to_snake
from .common import EconetDataCoordinator, Econet300Api
from .const import (
    AVAILABLE_NUMBER_OF_MIXERS,
    DOMAIN,
    ENTITY_DEVICE_CLASS_MAP,
    STATE_CLASS_MAP,
    SERVICE_COORDINATOR,
    SERVICE_API,
    SENSOR_MAP,
    ENTITY_PRECISION,
    ENTITY_UNIT_MAP,
    ENTITY_VALUE_PROCESSOR,
    ENTITY_CATEGORY,
    ENTITY_ICON,
)

from .entity import EconetEntity

_LOGGER = logging.getLogger(__name__)


@dataclass
class EconetSensorEntityDescription(SensorEntityDescription):
    """Describes Econet sensor entity."""

    process_val: Callable[[Any], Any] = lambda x: x


class EconetSensor(EconetEntity, SensorEntity):
    """Econet Sensor"""

    entity_description: EconetSensorEntityDescription

    def __init__(
        self,
        entity_description: EconetSensorEntityDescription,
        coordinator: EconetDataCoordinator,
        api: Econet300Api,
    ):
        """Initialize a new ecoNET sensor."""
        self.entity_description = entity_description
        self.api = api
        self._attr_native_value = None
        super().__init__(coordinator)
        _LOGGER.debug(
            "EconetSensor initialized with unique_id: %s, entity_description: %s",
            self.unique_id,
            self.entity_description,
        )

    @property
    def name(self):
        """Return the name of the sensor."""
        if self.entity_description.translation_key:
            _LOGGER.debug("Using translation key for sensor: %s", self.entity_description.translation_key)
            return f"entity.sensor.{self.entity_description.translation_key}"
        else:
            _LOGGER.debug("Using name for sensor: %s", self.entity_description.name)
            return self.entity_description.name

    def _sync_state(self, value):
        """Sync state."""
        _LOGGER.debug("Update EconetSensor entity: %s", self.entity_description.name)
        self._attr_native_value = self.entity_description.process_val(value)
        self.async_write_ha_state()


def create_entity_description(key: str) -> EconetSensorEntityDescription:
    """Creates Econect300 sensor entity based on supplied key"""
    map_key = SENSOR_MAP.get(key, key)
    _LOGGER.debug("SENSOR_MAP: %s", SENSOR_MAP)
    _LOGGER.debug("Creating entity description for key: %s, map_key: %s", key, map_key)
    entity_description = EconetSensorEntityDescription(
        key=key,
        device_class=ENTITY_DEVICE_CLASS_MAP.get(map_key, None),
        entity_category=ENTITY_CATEGORY.get(map_key, None),
        translation_key=camel_to_snake(map_key),
        icon=ENTITY_ICON.get(map_key, None),
        native_unit_of_measurement=ENTITY_UNIT_MAP.get(map_key, None),
        state_class=STATE_CLASS_MAP.get(map_key, None),
        suggested_display_precision=ENTITY_PRECISION.get(map_key, None),
        process_val=ENTITY_VALUE_PROCESSOR.get(map_key, lambda x: x),
    )
    _LOGGER.debug("Created entity description: %s", entity_description)
    return entity_description


def create_controller_sensors(coordinator: EconetDataCoordinator, api: Econet300Api):
    """Creating controller sensor entities"""
    entities: list[EconetSensor] = []
    coordinator_data = coordinator.data
    for data_key in SENSOR_MAP:
        if data_key in coordinator_data:
            entities.append(
                EconetSensor(create_entity_description(data_key), coordinator, api)
            )
            _LOGGER.debug(
                "Key: %s mapped, sensor entity will be added",
                data_key,
            )
            continue
        else:
            _LOGGER.debug(
                "Key: %s is not mapped, sensor entity will not be added",
                data_key,
            )

    return entities


def create_mixer_sensors(coordinator: EconetDataCoordinator, api: Econet300Api):
    """Create individual sensor descriptions for mixer sensors."""
    entities = []

    for i in range(1, AVAILABLE_NUMBER_OF_MIXERS + 1):
        description = EconetSensorEntityDescription(
            key=f"mixerTemp{i}",
            name=f"Mixer {i} temperature",
            translation_key=f"mixer_temp_{i}",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=0,
            process_val=lambda x: x,
        )
        if can_add(description, coordinator):
            entities.append(MixerSensor(description, coordinator, api, i))
        else:
            _LOGGER.debug(
                "Availability key: %s does not exist, entity will not be added",
                description.key,
            )
        description2 = EconetSensorEntityDescription(
            key=f"mixerSetTemp{i}",
            name=f"Mixer {i} set temperature",
            translation_key=f"mixer_{i}_set_temp",
            icon="mdi:thermometer",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            state_class=SensorStateClass.MEASUREMENT,
            device_class=SensorDeviceClass.TEMPERATURE,
            suggested_display_precision=0,
            process_val=lambda x: x,
        )

        if can_add(description2, coordinator):
            entities.append(MixerSensor(description2, coordinator, api, i))
        else:
            _LOGGER.debug(
                "Availability key: %s does not exist, entity will not be added",
                description2.key,
            )
    return entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id][SERVICE_COORDINATOR]
    api = hass.data[DOMAIN][entry.entry_id][SERVICE_API]

    entities: list[EconetSensor] = []
    entities.extend(create_controller_sensors(coordinator, api))

    return async_add_entities(entities)
