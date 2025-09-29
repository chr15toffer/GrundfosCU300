"""Serial port connection for GENIBus communication."""
import logging
import asyncio
import serial
import serial_asyncio

from .connection import Connection
from ..exceptions import ConnectionError as CU300ConnectionError

_LOGGER = logging.getLogger(__name__)


class SerialPort(Connection):
    """Serial port connection handler."""

    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        bytesize: int = serial.EIGHTBITS,
        parity: str = serial.PARITY_NONE,
        stopbits: int = serial.STOPBITS_ONE,
        timeout: float = 5.0,
    ) -> None:
        """Initialize serial port connection."""
        super().__init__()
        self._port = port
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._timeout = timeout
        
        _LOGGER.debug(
            "Initialized SerialPort: port=%s, baudrate=%d",
            self._port,
            self._baudrate,
        )

    async def connect(self) -> None:
        """Establish serial connection."""
        _LOGGER.debug("Connecting to serial port %s", self._port)
        
        try:
            self._reader, self._writer = await asyncio.wait_for(
                serial_asyncio.open_serial_connection(
                    url=self._port,
                    baudrate=self._baudrate,
                    bytesize=self._bytesize,
                    parity=self._parity,
                    stopbits=self._stopbits,
                    timeout=self._timeout,
                ),
                timeout=10,
            )
            _LOGGER.info("Connected to serial port %s", self._port)
            
        except asyncio.TimeoutError as err:
            _LOGGER.error("Connection to %s timed out", self._port)
            raise CU300ConnectionError(f"Connection timeout: {self._port}") from err
            
        except serial.SerialException as err:
            _LOGGER.error("Serial error on %s: %s", self._port, err)
            raise CU300ConnectionError(f"Serial error: {err}") from err
            
        except Exception as err:
            _LOGGER.error("Failed to connect to %s: %s", self._port, err)
            raise CU300ConnectionError(f"Connection failed: {err}") from err

    async def disconnect(self) -> None:
        """Close serial connection."""
        _LOGGER.debug("Disconnecting from %s", self._port)
        
        if self._writer:
            try:
                self._writer.close()
                await asyncio.wait_for(self._writer.wait_closed(), timeout=5)
                _LOGGER.info("Disconnected from %s", self._port)
                
            except asyncio.TimeoutError:
                _LOGGER.warning("Disconnect timeout for %s", self._port)
                
            except Exception as err:
                _LOGGER.error("Error disconnecting from %s: %s", self._port, err)
                
            finally:
                self._reader = None
                self._writer = None

    async def write(self, data: bytes | bytearray) -> None:
        """Write data to serial port."""
        if not self._writer:
            raise CU300ConnectionError("Serial port not connected")
        
        _LOGGER.debug("Writing to %s: %s", self._port, data.hex())
        
        try:
            self._writer.write(bytes(data))
            await asyncio.wait_for(self._writer.drain(), timeout=5)
            _LOGGER.debug("Write completed to %s", self._port)
            
        except asyncio.TimeoutError as err:
            _LOGGER.error("Write timeout on %s", self._port)
            raise CU300ConnectionError(f"Write timeout: {self._port}") from err
            
        except Exception as err:
            _LOGGER.error("Write error on %s: %s", self._port, err)
            raise CU300ConnectionError(f"Write error: {err}") from err

    async def read(self, size: int = 1) -> bytes:
        """Read data from serial port.
        
        Note: This is kept for compatibility but protocol.py should use
        _read_frame() which properly handles GENIBus frame structure.
        """
        if not self._reader:
            raise CU300ConnectionError("Serial port not connected")
        
        _LOGGER.debug("Reading %d bytes from %s", size, self._port)
        
        try:
            data = await asyncio.wait_for(
                self._reader.read(size),
                timeout=self._timeout,
            )
            _LOGGER.debug("Read from %s: %s", self._port, data.hex())
            return data
            
        except asyncio.TimeoutError:
            _LOGGER.warning("Read timeout on %s", self._port)
            return b""
            
        except Exception as err:
            _LOGGER.error("Read error on %s: %s", self._port, err)
            raise CU300ConnectionError(f"Read error: {err}") from err

    async def read_exact(self, size: int) -> bytes:
        """Read exact number of bytes."""
        if not self._reader:
            raise CU300ConnectionError("Serial port not connected")
        
        try:
            data = await asyncio.wait_for(
                self._reader.readexactly(size),
                timeout=self._timeout,
            )
            return data
            
        except asyncio.IncompleteReadError as err:
            _LOGGER.error(
                "Incomplete read on %s: expected %d, got %d",
                self._port,
                size,
                len(err.partial),
            )
            raise CU300ConnectionError("Incomplete read") from err
            
        except asyncio.TimeoutError as err:
            _LOGGER.error("Read timeout on %s", self._port)
            raise CU300ConnectionError("Read timeout") from err

    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._reader is not None and self._writer is not None
