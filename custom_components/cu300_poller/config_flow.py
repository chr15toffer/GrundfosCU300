"""Config flow for CU300 Poller integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_TYPE, CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONNECTION_TYPE_SERIAL,
    CONNECTION_TYPE_TCP,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_TCP_PORT,
)

_LOGGER = logging.getLogger(__name__)


class CU300ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CU300 Poller."""

    VERSION = 1

    def __init__(self):
        """Initialize config flow."""
        self._connection_type = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - choose connection type."""
        if user_input is not None:
            self._connection_type = user_input[CONF_TYPE]
            
            # Move to appropriate next step based on connection type
            if self._connection_type == CONNECTION_TYPE_SERIAL:
                return await self.async_step_serial()
            return await self.async_step_tcp()

        # Show connection type selection form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TYPE, default=CONNECTION_TYPE_SERIAL): vol.In(
                        {
                            CONNECTION_TYPE_SERIAL: "Serial",
                            CONNECTION_TYPE_TCP: "TCP",
                        }
                    ),
                }
            ),
        )

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle serial connection configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Add connection type to user input
            user_input[CONF_TYPE] = CONNECTION_TYPE_SERIAL
            
            # Validate connection
            try:
                await self._test_connection(user_input)
                
                # Create unique ID
                unique_id = f"serial_{user_input[CONF_PORT]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Create entry
                return self.async_create_entry(
                    title=f"CU300 ({user_input[CONF_PORT]})",
                    data=user_input,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except AlreadyConfigured:
                return self.async_abort(reason="already_configured")
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during serial setup")
                errors["base"] = "unknown"

        # Show serial configuration form
        return self.async_show_form(
            step_id="serial",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PORT, default="/dev/ttyUSB0"): str,
                    vol.Optional(
                        CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                    ): cv.positive_int,
                }
            ),
            errors=errors,
        )

    async def async_step_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle TCP connection configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Add connection type to user input
            user_input[CONF_TYPE] = CONNECTION_TYPE_TCP
            
            # Validate connection
            try:
                await self._test_connection(user_input)
                
                # Create unique ID
                unique_id = f"tcp_{user_input[CONF_HOST]}_{user_input[CONF_PORT]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Create entry
                return self.async_create_entry(
                    title=f"CU300 ({user_input[CONF_HOST]}:{user_input[CONF_PORT]})",
                    data=user_input,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except AlreadyConfigured:
                return self.async_abort(reason="already_configured")
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during TCP setup")
                errors["base"] = "unknown"

        # Show TCP configuration form
        return self.async_show_form(
            step_id="tcp",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_TCP_PORT): cv.port,
                    vol.Optional(
                        CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                    ): cv.positive_int,
                }
            ),
            errors=errors,
        )

    async def _test_connection(self, config: dict[str, Any]) -> None:
        """Test if we can connect to the device."""
        try:
            # Log the config we received
            _LOGGER.debug("Testing connection with config: %s", config)
            _LOGGER.debug("CONF_TYPE = '%s', value = %s", CONF_TYPE, config.get(CONF_TYPE))
            _LOGGER.debug("CONF_PORT = '%s', value = %s", CONF_PORT, config.get(CONF_PORT))
            _LOGGER.debug("CONF_HOST = '%s', value = %s", CONF_HOST, config.get(CONF_HOST))
            
            # Import here to avoid issues if library isn't installed yet
            from .genibus.protocol import CU300Protocol
            from .genibus.exceptions import ConnectionError as CU300ConnectionError

            # Get connection parameters
            connection_type = config.get(CONF_TYPE)
            host = config.get(CONF_HOST)
            port = config.get(CONF_PORT)
            
            # Validate we have required parameters
            if connection_type == CONNECTION_TYPE_SERIAL and not port:
                _LOGGER.error("Serial connection requires port, but got: %s", port)
                raise CannotConnect("Port not provided for serial connection")
            
            if connection_type == CONNECTION_TYPE_TCP and (not host or not port):
                _LOGGER.error("TCP connection requires host and port, got host=%s, port=%s", host, port)
                raise CannotConnect("Host and port required for TCP connection")
            
            # Log what we're trying to connect to
            _LOGGER.info(
                "Testing connection: type=%s, host=%s, port=%s",
                connection_type,
                host,
                port,
            )

            protocol = CU300Protocol(
                connection_type=connection_type,
                host=host,
                port=port,
            )

            # Try to connect with timeout
            await asyncio.wait_for(protocol.connect(), timeout=15)
            
            # Disconnect after successful test
            await protocol.disconnect()
            
            _LOGGER.info("Connection test successful")

        except asyncio.TimeoutError as err:
            _LOGGER.error("Connection test timed out")
            raise CannotConnect from err
        except CU300ConnectionError as err:
            _LOGGER.error("Connection test failed: %s", err)
            raise CannotConnect from err
        except ImportError as err:
            _LOGGER.error("Failed to import protocol library: %s", err)
            raise CannotConnect from err
        except Exception as err:
            _LOGGER.exception("Unexpected error during connection test")
            raise CannotConnect from err

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> CU300OptionsFlow:
        """Get the options flow for this handler."""
        return CU300OptionsFlow(config_entry)


class CU300OptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for CU300 Poller."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL,
                            self.config_entry.data.get(
                                CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                            ),
                        ),
                    ): cv.positive_int,
                }
            ),
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class AlreadyConfigured(Exception):
    """Error to indicate device is already configured."""
