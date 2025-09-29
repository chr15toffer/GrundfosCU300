"""High-level protocol handler for CU300 using GENIBus."""
import asyncio
import logging
from typing import Any

from .linklayer.serialport import SerialPort
from .linklayer.tcpclient import TcpClient
from .apdu import (
    APDU,
    Header,
    createConnectRequestPDU,
    createGetValuesPDU,
    createSetCommandsPDU,
    createSetValuesPDU,
)
from . import gbdefs
from .utils import crc
from .devices.db import DeviceDB
from .exceptions import ProtocolError, ConnectionError as CU300ConnectionError

_LOGGER = logging.getLogger(__name__)


class CU300Protocol:
    """High-level protocol handler for CU300."""

    def __init__(
        self,
        connection_type: str,
        host: str | None = None,
        port: str | None = None,
        device_addr: int = 0x20,
        source_addr: int = 0x04,
    ) -> None:
        """Initialize protocol handler."""
        self._connection_type = connection_type
        self._host = host
        self._port = port
        self._device_addr = device_addr
        self._source_addr = source_addr
        self._connection = None
        self._lock = asyncio.Lock()
        self._device_db = DeviceDB()
        
        _LOGGER.debug(
            "Initialized CU300Protocol: type=%s, host=%s, port=%s",
            connection_type,
            host,
            port,
        )

    async def connect(self) -> None:
        """Connect to the device and perform handshake."""
        _LOGGER.debug("Connecting to device")
        
        try:
            # Create connection
            if self._connection_type == "tcp":
                if not self._host:
                    raise CU300ConnectionError("Host required for TCP connection")
                self._connection = TcpClient(self._host, self._port)
            else:
                if not self._port:
                    raise CU300ConnectionError("Port required for serial connection")
                self._connection = SerialPort(self._port)

            # Establish connection
            await asyncio.wait_for(self._connection.connect(), timeout=10)
            _LOGGER.debug("Physical connection established")

            # Send connect request using APDU helper
            connect_pdu = createConnectRequestPDU(self._source_addr)
            response = await self._send_and_receive(connect_pdu)
            
            if not response:
                raise ProtocolError("No response to connect request")

            _LOGGER.info("Successfully connected to CU300")

        except asyncio.TimeoutError as err:
            _LOGGER.error("Connection timeout")
            raise CU300ConnectionError("Connection timeout") from err
        except Exception as err:
            _LOGGER.error("Connection failed: %s", err)
            if self._connection:
                await self._connection.disconnect()
                self._connection = None
            raise CU300ConnectionError(f"Connection failed: {err}") from err

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        _LOGGER.debug("Disconnecting from device")
        if self._connection:
            try:
                await self._connection.disconnect()
            except Exception as err:
                _LOGGER.error("Error during disconnect: %s", err)
            finally:
                self._connection = None

    async def reconnect(self) -> None:
        """Reconnect to the device."""
        _LOGGER.info("Attempting reconnection")
        await self.disconnect()
        await asyncio.sleep(1)  # Brief delay before reconnecting
        await self.connect()

    async def poll_data(self) -> dict[str, Any]:
        """Poll measured data from the device."""
        async with self._lock:
            try:
                # Create data request PDU using APDU helpers
                header = Header(
                    gbdefs.FrameType.SD_DATA_REQUEST,
                    self._device_addr,
                    self._source_addr,
                )
                
                # Request key measurements
                measurements = ['h', 'q', 'speed', 'act_mode1', 'alarm_code']
                
                pdu = createGetValuesPDU(
                    klass=gbdefs.APDUClass.MEASURED_DATA,
                    header=header,
                    measurements=measurements,
                )
                
                response = await self._send_and_receive(pdu)
                
                if not response:
                    raise ProtocolError("No response received")

                # Parse response
                data = self._parse_response(response)
                _LOGGER.debug("Parsed data: %s", data)
                
                return data

            except asyncio.TimeoutError as err:
                _LOGGER.error("Timeout polling data")
                raise ProtocolError("Timeout polling data") from err
            except Exception as err:
                _LOGGER.error("Error polling data: %s", err)
                raise

    async def start_pump(self) -> None:
        """Start the pump."""
        async with self._lock:
            try:
                header = Header(
                    gbdefs.FrameType.SD_DATA_REQUEST,
                    self._device_addr,
                    self._source_addr,
                )
                
                pdu = createSetCommandsPDU(header, commands=['REMOTE', 'START'])
                
                response = await self._send_and_receive(pdu)
                
                if not response:
                    raise ProtocolError("No response to start command")
                
                _LOGGER.info("Pump started successfully")

            except Exception as err:
                _LOGGER.error("Failed to start pump: %s", err)
                raise ProtocolError(f"Failed to start pump: {err}") from err

    async def stop_pump(self) -> None:
        """Stop the pump."""
        async with self._lock:
            try:
                header = Header(
                    gbdefs.FrameType.SD_DATA_REQUEST,
                    self._device_addr,
                    self._source_addr,
                )
                
                pdu = createSetCommandsPDU(header, commands=['STOP'])
                
                response = await self._send_and_receive(pdu)
                
                if not response:
                    raise ProtocolError("No response to stop command")
                
                _LOGGER.info("Pump stopped successfully")

            except Exception as err:
                _LOGGER.error("Failed to stop pump: %s", err)
                raise ProtocolError(f"Failed to stop pump: {err}") from err

    async def set_reference(self, value: int) -> None:
        """Set reference value (0-100%)."""
        if not 0 <= value <= 100:
            raise ValueError("Reference value must be between 0 and 100")

        async with self._lock:
            try:
                header = Header(
                    gbdefs.FrameType.SD_DATA_REQUEST,
                    self._device_addr,
                    self._source_addr,
                )
                
                pdu = createSetValuesPDU(
                    header,
                    references=[('ref', value)],
                )
                
                response = await self._send_and_receive(pdu)
                
                if not response:
                    raise ProtocolError("No response to set reference")
                
                _LOGGER.info("Reference set to %s%%", value)

            except Exception as err:
                _LOGGER.error("Failed to set reference: %s", err)
                raise ProtocolError(f"Failed to set reference: {err}") from err

    async def _send_and_receive(self, pdu: bytearray) -> bytearray:
        """Send PDU and receive response."""
        if not self._connection:
            raise CU300ConnectionError("Not connected")

        # PDU should already have CRC from APDU functions, but verify
        if not crc.check_tel(pdu, silent=True):
            pdu = crc.append_tel(pdu)

        _LOGGER.debug("Sending PDU: %s", pdu.hex())
        
        try:
            await self._connection.write(pdu)
            response = await asyncio.wait_for(
                self._read_frame(),
                timeout=5,
            )
            _LOGGER.debug("Received response: %s", response.hex())
            return response

        except asyncio.TimeoutError as err:
            _LOGGER.error("Timeout waiting for response")
            raise ProtocolError("Response timeout") from err

    async def _read_frame(self) -> bytearray:
        """Read a complete GENIBus frame."""
        if not self._connection or not self._connection._reader:
            raise CU300ConnectionError("No active connection")

        # Read start delimiter
        start = await self._connection._reader.read(1)
        if not start:
            raise ProtocolError("No data received")

        start_byte = start[0]
        if start_byte not in [
            gbdefs.FrameType.SD_DATA_REQUEST,
            gbdefs.FrameType.SD_DATA_REPLY,
            gbdefs.FrameType.SD_DATA_MESSAGE,
        ]:
            raise ProtocolError(f"Invalid start delimiter: 0x{start_byte:02x}")

        # Read length byte
        length_data = await self._connection._reader.read(1)
        if not length_data:
            raise ProtocolError("Failed to read length byte")
        
        length = length_data[0]
        
        if length > gbdefs.MAX_PDU_LEN:
            raise ProtocolError(f"Invalid frame length: {length}")

        # Read remaining data (length + 2 for CRC)
        remaining_length = length + 2
        remaining = await self._connection._reader.read(remaining_length)
        
        if len(remaining) != remaining_length:
            raise ProtocolError(
                f"Incomplete frame: expected {remaining_length}, got {len(remaining)}"
            )

        # Assemble complete frame
        frame = start + length_data + remaining

        # Verify CRC
        if not crc.check_tel(frame, silent=True):
            raise ProtocolError("CRC check failed")

        return frame

    def _parse_response(self, response: bytearray) -> dict[str, Any]:
        """Parse response frame into data dictionary."""
        try:
            apdu = APDU.from_bytes(response)
            
            if not apdu:
                raise ProtocolError("Failed to parse APDU")

            # Extract values with proper naming
            data = {
                'head': apdu.get_value('h'),
                'flow': apdu.get_value('q'),
                'speed': apdu.get_value('speed'),
                'power': apdu.get_value('p'),
                'act_mode1': apdu.get_value('act_mode1'),
                'alarm_code': apdu.get_value('alarm_code'),
            }

            # Filter out None values
            return {k: v for k, v in data.items() if v is not None}

        except Exception as err:
            _LOGGER.error("Error parsing response: %s", err)
            raise ProtocolError(f"Failed to parse response: {err}") from err
