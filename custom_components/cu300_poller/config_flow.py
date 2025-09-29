"""Config flow for CU300 Poller integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_TYPE, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
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


async def validate_connection(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate the connection to the CU300 device."""
    from .genibus.protocol import CU300Protocol
    from .genibus.exceptions import ConnectionError as CU300ConnectionError

    connection_type = data[CONF_TYPE]
    host = data.get(CONF_HOST)
    port = data.get(CONF_PORT)

    protocol = CU300Protocol(
        connection_type=connection_type,
        host=host,
        port=port,
    )

    try:
        await protocol.connect()
        await protocol.disconnect()
        return {"title": f"CU300 ({port or host})"}
    except CU300ConnectionError as err:
        raise CannotConnect from err
    except Exception as err:
        _LOGGER.exception("Unexpected error during validation")
        raise CannotConnect from err


class CU300ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CU300 Poller."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_connection(self.hass, user_input)
                
                # Create unique ID based on connection details
                if user_input[CONF_TYPE] == CONNECTION_TYPE_SERIAL:
                    unique_id = f"serial_{user_input[CONF_PORT]}"
                else:
                    unique_id = f"tcp_{user_input[CONF_HOST]}_{user_input[CONF_PORT]}"
                
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Show form
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
            errors=errors,
        )

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle serial connection configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_TYPE] = CONNECTION_TYPE_SERIAL
            try:
                info = await validate_connection(self.hass, user_input)
                
                unique_id = f"serial_{user_input[CONF_PORT]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

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
            user_input[CONF_TYPE] = CONNECTION_TYPE_TCP
            try:
                info = await validate_connection(self.hass, user_input)
                
                unique_id = f"tcp_{user_input[CONF_HOST]}_{user_input[CONF_PORT]}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

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
                        default=self.config_entry.data.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): cv.positive_int,
                }
            ),
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
