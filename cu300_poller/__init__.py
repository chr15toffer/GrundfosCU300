     """CU300 Poller integration."""
     import asyncio
     import logging
     import voluptuous as vol
     from homeassistant.core import HomeAssistant
     from homeassistant.const import CONF_TYPE, CONF_HOST, CONF_PORT
     import homeassistant.helpers.config_validation as cv
     from .const import DOMAIN, CONNECTION_TYPE_SERIAL, CONNECTION_TYPE_TCP
     from .cu300_poller import CU300Poller

     _LOGGER = logging.getLogger(__name__)

     CONFIG_SCHEMA = vol.Schema(
         {
             DOMAIN: vol.Schema(
                 {
                     vol.Required(CONF_TYPE): vol.In([CONNECTION_TYPE_SERIAL, CONNECTION_TYPE_TCP]),
                     vol.Optional(CONF_HOST): cv.string,
                     vol.Required(CONF_PORT): cv.string,
                 }
             )
         },
         extra=vol.ALLOW_EXTRA,
     )

     async def async_setup(hass: HomeAssistant, config: dict) -> bool:
         """Set up the CU300 Poller integration from YAML."""
         _LOGGER.debug("Starting setup for cu300_poller")
         if DOMAIN not in config:
             _LOGGER.debug("No cu300_poller configuration found")
             return True

         conf = config[DOMAIN]
         connection_type = conf.get(CONF_TYPE)
         host = conf.get(CONF_HOST)
         port = conf.get(CONF_PORT)
         _LOGGER.debug(f"Config: type={connection_type}, host={host}, port={port}")

         # Initialize poller
         try:
             poller = CU300Poller(connection_type, host=host, port=port)
             _LOGGER.debug("CU300Poller initialized")
             await asyncio.wait_for(poller.connect(), timeout=15)
             _LOGGER.debug("Poller connected")
             hass.data.setdefault(DOMAIN, {})["yaml"] = poller
         except asyncio.TimeoutError:
             _LOGGER.error(f"Setup failed: Connection to {port or host} timed out")
             return False
         except Exception as e:
             _LOGGER.error(f"Setup failed: Failed to connect to CU300: {e.__class__.__name__}: {str(e)}")
             return False

         # Set up platforms (sensor)
         _LOGGER.debug("Setting up sensor platform")
         await hass.async_create_task(
             hass.config.async_setup_platforms(DOMAIN, ["sensor"])
         )
         _LOGGER.debug("Sensor platform setup completed")

         # Start polling
         async def async_update_data():
             _LOGGER.debug("Starting polling loop")
             while True:
                 try:
                     await poller.poll()
                 except Exception as e:
                     _LOGGER.error(f"Error polling CU300: {e.__class__.__name__}: {str(e)}")
                 await asyncio.sleep(30)  # Poll every 30 seconds

         hass.async_create_task(async_update_data())
         _LOGGER.debug("Polling task created")

         # Register services
         async def handle_start_pump(call):
             _LOGGER.debug("Service call: start_pump")
             await poller.start_pump(call)

         async def handle_stop_pump(call):
             _LOGGER.debug("Service call: stop_pump")
             await poller.stop_pump(call)

         async def handle_set_reference(call):
             _LOGGER.debug("Service call: set_reference")
             await poller.set_reference(call)

         async def handle_test_connection(call):
             _LOGGER.debug("Service call: test_connection")
             await poller.test_connection(call)

         hass.services.async_register(DOMAIN, "start_pump", handle_start_pump)
         hass.services.async_register(DOMAIN, "stop_pump", handle_stop_pump)
         hass.services.async_register(DOMAIN, "set_reference", handle_set_reference)
         hass.services.async_register(DOMAIN, "test_connection", handle_test_connection)
         _LOGGER.debug("Services registered")

         _LOGGER.debug("Setup completed successfully")
         return True