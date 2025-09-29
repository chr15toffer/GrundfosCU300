"""Number platform for CU300 Poller."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CU300Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up CU300 number platform."""
    coordinator: CU300Coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [CU300ReferenceNumber(coordinator, entry)]

    async_add_entities(entities)
    _LOGGER.debug("Added CU300 reference number entity")


class CU300ReferenceNumber(CoordinatorEntity[CU300Coordinator], NumberEntity):
    """Representation of a CU300 reference value number entity."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: CU300Coordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._attr_name = "CU300 Reference"
        self._attr_unique_id = f"{entry.entry_id}_reference"
        self._attr_icon = "mdi:target"
        self._attr_native_unit_of_measurement = PERCENTAGE
        
        # Device info for grouping entities
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Grundfos CU300",
            "manufacturer": "Grundfos",
            "model": "CU300",
            "sw_version": "1.0",
        }

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        if self.coordinator.data is None:
            return None
        
        # Get reference value from data (adjust key if needed)
        ref_value = self.coordinator.data.get('reference')
        return ref_value if ref_value is not None else 50  # Default to 50%

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.connected

    async def async_set_native_value(self, value: float) -> None:
        """Set new value."""
        try:
            await self.coordinator.async_set_reference(int(value))
        except Exception as err:
            _LOGGER.error("Failed to set reference value: %s", err)
            raise
