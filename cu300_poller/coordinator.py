"""Data update coordinator for CU300 Poller."""
import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .genibus.protocol import CU300Protocol
from .genibus.exceptions import ProtocolError, ConnectionError as CU300ConnectionError

_LOGGER = logging.getLogger(__name__)

class CU300Coordinator(DataUpdateCoordinator):
    """Coordinator to manage CU300 data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        connection_type: str,
        host: str | None = None,
        port: str | None = None,
        update_interval: int = 30,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        self.connection_type = connection_type
        self.host = host
        self.port = port
        self.protocol: CU300Protocol | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._connected = False

    async def async_setup(self) -> None:
        """Set up the coordinator and establish connection."""
        try:
            self.protocol = CU300Protocol(
                connection_type=self.connection_type,
                host=self.host,
                port=self.port,
            )
            await asyncio.wait_for(self.protocol.connect(), timeout=15)
            self._connected = True
            _LOGGER.info(
                "Successfully connected to CU300 at %s",
                self.port or f"{self.host}:{self.port}",
            )
        except asyncio.TimeoutError as err:
            _LOGGER.error("Connection to CU300 timed out")
            raise ConfigEntryNotReady("Connection timed out") from err
        except CU300ConnectionError as err:
            _LOGGER.error("Failed to connect to CU300: %s", err)
            raise ConfigEntryNotReady(f"Connection failed: {err}") from err
        except Exception as err:
            _LOGGER.error("Unexpected error during setup: %s", err)
            raise ConfigEntryNotReady(f"Setup failed: {err}") from err

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from CU300."""
        if not self._connected:
            _LOGGER.warning("Not connected, attempting to reconnect")
            await self._async_reconnect()
            if not self._connected:
                raise UpdateFailed("Not connected to CU300")

        try:
            data = await asyncio.wait_for(
                self.protocol.poll_data(),
                timeout=10,
            )
            _LOGGER.debug("Successfully polled data: %s", data)
            return data

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout polling CU300 data")
            self._connected = False
            self._schedule_reconnect()
            raise UpdateFailed("Timeout polling data")

        except ProtocolError as err:
            _LOGGER.error("Protocol error: %s", err)
            raise UpdateFailed(f"Protocol error: {err}")

        except CU300ConnectionError as err:
            _LOGGER.error("Connection error: %s", err)
            self._connected = False
            self._schedule_reconnect()
            raise UpdateFailed(f"Connection error: {err}")

        except Exception as err:
            _LOGGER.exception("Unexpected error polling data")
            raise UpdateFailed(f"Unexpected error: {err}")

    async def _async_reconnect(self) -> None:
        """Attempt to reconnect to the device."""
        if self.protocol is None:
            return

        try:
            _LOGGER.info("Attempting to reconnect to CU300")
            await asyncio.wait_for(self.protocol.reconnect(), timeout=15)
            self._connected = True
            _LOGGER.info("Successfully reconnected to CU300")
        except Exception as err:
            _LOGGER.error("Failed to reconnect: %s", err)
            self._connected = False

    def _schedule_reconnect(self) -> None:
        """Schedule a reconnection attempt."""
        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = self.hass.async_create_task(
                self._async_reconnect()
            )

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        if self.protocol:
            try:
                await self.protocol.disconnect()
                _LOGGER.info("Disconnected from CU300")
            except Exception as err:
                _LOGGER.error("Error disconnecting: %s", err)

    async def async_start_pump(self) -> None:
        """Start the pump."""
        if not self._connected or self.protocol is None:
            raise UpdateFailed("Not connected to CU300")

        try:
            await asyncio.wait_for(self.protocol.start_pump(), timeout=5)
            _LOGGER.info("Pump started successfully")
            # Request immediate update
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to start pump: %s", err)
            raise UpdateFailed(f"Failed to start pump: {err}")

    async def async_stop_pump(self) -> None:
        """Stop the pump."""
        if not self._connected or self.protocol is None:
            raise UpdateFailed("Not connected to CU300")

        try:
            await asyncio.wait_for(self.protocol.stop_pump(), timeout=5)
            _LOGGER.info("Pump stopped successfully")
            # Request immediate update
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to stop pump: %s", err)
            raise UpdateFailed(f"Failed to stop pump: {err}")

    async def async_set_reference(self, value: int) -> None:
        """Set reference value."""
        if not self._connected or self.protocol is None:
            raise UpdateFailed("Not connected to CU300")

        try:
            await asyncio.wait_for(
                self.protocol.set_reference(value),
                timeout=5,
            )
            _LOGGER.info("Reference set to %s successfully", value)
            # Request immediate update
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set reference: %s", err)
            raise UpdateFailed(f"Failed to set reference: {err}")

    @property
    def connected(self) -> bool:
        """Return connection status."""
        return self._connected
