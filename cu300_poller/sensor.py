"""Sensor platform for CU300 Poller."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import async_get_current_platform
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the sensor platform."""
    poller = hass.data[DOMAIN]
    sensors = [
        CU300Sensor(poller, "head", "Head", "m"),
        CU300Sensor(poller, "flow", "Flow", "m³/h"),
        CU300Sensor(poller, "speed", "Speed", "%"),
        CU300Sensor(poller, "alarm_code", "Alarm Code", ""),
    ]
    async_add_entities(sensors)

    # Poll every 30 seconds (adjust as needed)
    platform = async_get_current_platform()
    platform.async_add_job(poller.poll)  # Initial poll
    hass.loop.create_task(async_periodic_poll(poller))

async def async_periodic_poll(poller):
    while True:
        await poller.poll()
        await asyncio.sleep(30)  # Poll interval

class CU300Sensor(SensorEntity):
    """Representation of a CU300 sensor."""

    def __init__(self, poller, key, name, unit):
        self._poller = poller
        self._key = key
        self._name = name
        self._unit = unit
        self._state = None

    @property
    def name(self):
        return f"CU300 {self._name}"

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit

    def update(self):
        self._state = self._poller.get_data(self._key)