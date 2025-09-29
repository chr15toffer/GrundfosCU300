"""Switch platform for CU300 Poller."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up CU300 switch platform."""
    coordinator: CU300Coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [CU300PumpSwitch(coordinator, entry)]

    async_add_entities(entities)
    _LOGGER.debug("Added CU300 pump switch")


class CU300PumpSwitch(CoordinatorEntity[CU300Coordinator], SwitchEntity):
    """Representation of a CU300 pump switch."""

    def __init__(
        self,
        coordinator: CU300Coordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._attr_name = "CU300 Pump"
        self._attr_unique_id = f"{entry.entry_id}_pump_switch"
        self._attr_icon = "mdi:pump"
        
        # Device info for grouping entities
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Grundfos CU300",
            "manufacturer": "Grundfos",
            "model": "CU300",
            "sw_version": "1.0",
        }

    @property
    def is_on(self) -> bool | None:
        """Return true if pump is on."""
        if self.coordinator.data is None:
            return None
        
        # Check operating mode - adjust based on actual CU300 values
        act_mode = self.coordinator.data.get('act_mode1')
        if act_mode is None:
            return None
        
        # Typically, mode > 0 means running (adjust as needed)
        return act_mode > 0

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.connected

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the pump on."""
        try:
            await self.coordinator.async_start_pump()
        except Exception as err:
            _LOGGER.error("Failed to turn on pump: %s", err)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the pump off."""
        try:
            await self.coordinator.async_stop_pump()
        except Exception as err:
            _LOGGER.error("Failed to turn off pump: %s", err)
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if self.coordinator.data:
            return {
                "speed": self.coordinator.data.get('speed'),
                "alarm_code": self.coordinator.data.get('alarm_code'),
            }
        return None
