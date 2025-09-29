"""CU300 Poller integration."""
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_TYPE, CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)
from .coordinator import CU300Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER]

# YAML configuration schema (for backward compatibility)
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_TYPE): vol.In([CONNECTION_TYPE_SERIAL, CONNECTION_TYPE_TCP]),
                vol.Optional(CONF_HOST): cv.string,
                vol.Required(CONF_PORT): cv.string,
                vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# Service schemas
SERVICE_SET_REFERENCE_SCHEMA = vol.Schema(
    {
        vol.Required("reference"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the CU300 Poller integration from YAML."""
    if DOMAIN not in config:
        return True

    # YAML configuration is deprecated but supported for backward compatibility
    _LOGGER.warning(
        "YAML configuration for CU300 Poller is deprecated. "
        "Please migrate to UI configuration."
    )

    conf = config[DOMAIN]
    
    # Store YAML config for use in async_setup_entry if no config entries exist
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["yaml_config"] = conf

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CU300 Poller from a config entry."""
    _LOGGER.debug("Setting up CU300 Poller entry: %s", entry.entry_id)

    connection_type = entry.data[CONF_TYPE]
    host = entry.data.get(CONF_HOST)
    port = entry.data.get(CONF_PORT)
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    # Create coordinator
    coordinator = CU300Coordinator(
        hass,
        connection_type=connection_type,
        host=host,
        port=port,
        update_interval=update_interval,
    )

    # Set up connection
    try:
        await coordinator.async_setup()
    except ConfigEntryNotReady as err:
        _LOGGER.error("Failed to set up CU300: %s", err)
        raise

    # Perform initial data fetch
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def handle_start_pump(call: ServiceCall) -> None:
        """Handle start pump service call."""
        _LOGGER.debug("Service call: start_pump")
        try:
            await coordinator.async_start_pump()
        except Exception as err:
            _LOGGER.error("Failed to start pump: %s", err)

    async def handle_stop_pump(call: ServiceCall) -> None:
        """Handle stop pump service call."""
        _LOGGER.debug("Service call: stop_pump")
        try:
            await coordinator.async_stop_pump()
        except Exception as err:
            _LOGGER.error("Failed to stop pump: %s", err)

    async def handle_set_reference(call: ServiceCall) -> None:
        """Handle set reference service call."""
        reference = call.data["reference"]
        _LOGGER.debug("Service call: set_reference to %s", reference)
        try:
            await coordinator.async_set_reference(reference)
        except Exception as err:
            _LOGGER.error("Failed to set reference: %s", err)

    # Register services (only once)
    if not hass.services.has_service(DOMAIN, "start_pump"):
        hass.services.async_register(DOMAIN, "start_pump", handle_start_pump)
        hass.services.async_register(DOMAIN, "stop_pump", handle_stop_pump)
        hass.services.async_register(
            DOMAIN,
            "set_reference",
            handle_set_reference,
            schema=SERVICE_SET_REFERENCE_SCHEMA,
        )

    _LOGGER.info("CU300 Poller setup completed successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading CU300 Poller entry: %s", entry.entry_id)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Shutdown coordinator
        coordinator: CU300Coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_shutdown()

        # Remove entry data
        hass.data[DOMAIN].pop(entry.entry_id)

        # Remove services if this is the last entry
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "start_pump")
            hass.services.async_remove(DOMAIN, "stop_pump")
            hass.services.async_remove(DOMAIN, "set_reference")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
