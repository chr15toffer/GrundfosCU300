"""Sensor platform for CU300 Poller."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfVolumeFlowRate,
    UnitOfLength,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CU300Coordinator

_LOGGER = logging.getLogger(__name__)


SENSOR_TYPES = [
    {
        "key": "head",
        "name": "Head",
        "icon": "mdi:gauge",
        "unit": UnitOfLength.METERS,
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "flow",
        "name": "Flow",
        "icon": "mdi:water-pump",
        "unit": UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "speed",
        "name": "Speed",
        "icon": "mdi:speedometer",
        "unit": PERCENTAGE,
        "device_class": None,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "power",
        "name": "Power",
        "icon": "mdi:lightning-bolt",
        "unit": "W",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "key": "alarm_code",
        "name": "Alarm Code",
        "icon": "mdi:alert-circle",
        "unit": None,
        "device_class": None,
        "state_class": None,
    },
    {
        "key": "act_mode1",
        "name": "Operating Mode",
        "icon": "mdi:cog",
        "unit": None,
        "device_class": None,
        "state_class": None,
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CU300 sensor platform."""
    coordinator: CU300Coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        CU300Sensor(coordinator, entry, sensor_config)
        for sensor_config in SENSOR_TYPES
    ]

    async_add_entities(entities)
    _LOGGER.debug("Added %d CU300 sensors", len(entities))


class CU300Sensor(CoordinatorEntity[CU300Coordinator], SensorEntity):
    """Representation of a CU300 sensor."""

    def __init__(
        self,
        coordinator: CU300Coordinator,
        entry: ConfigEntry,
        sensor_config: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = sensor_config["key"]
        self._attr_name = f"CU300 {sensor_config['name']}"
        self._attr_unique_id = f"{entry.entry_id}_{self._key}"
        self._attr_icon = sensor_config["icon"]
        self._attr_native_unit_of_measurement = sensor_config["unit"]
        self._attr_device_class = sensor_config["device_class"]
        self._attr_state_class = sensor_config["state_class"]
        
        # Device info for grouping entities
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Grundfos CU300",
            "manufacturer": "Grundfos",
            "model": "CU300",
            "sw_version": "1.0",
        }

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.connected

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if self._key == "alarm_code" and self.native_value:
            return {
                "alarm_description": self._get_alarm_description(self.native_value)
            }
        return None

    def _get_alarm_description(self, code: int) -> str:
        """Get human-readable alarm description."""
        # Map alarm codes to descriptions (adjust based on CU300 manual)
        alarm_map = {
            0: "No alarm",
            1: "Low water level",
            2: "High temperature",
            3: "Motor overload",
            4: "Dry running",
            5: "Communication error",
        }
        return alarm_map.get(code, f"Unknown alarm code: {code}")
