     import logging
     import serial
     import asyncio
     import serial_asyncio
     from .connection import Connection

     _logger = logging.getLogger(__name__)

     class SerialPort(Connection):
         def __init__(self, port):
             super().__init__()
             self._port = port
             self._reader = None
             self._writer = None
             _logger.debug(f"Initialized SerialPort with port={self._port}")

         async def connect(self):
             _logger.debug(f"Attempting to connect to {self._port}")
             try:
                 self._reader, self._writer = await asyncio.wait_for(
                     serial_asyncio.open_serial_connection(
                         url=self._port,
                         baudrate=9600,
                         parity=serial.PARITY_NONE,
                         stopbits=serial.STOPBITS_ONE,
                         bytesize=serial.EIGHTBITS,
                         timeout=5
                     ),
                     timeout=10
                 )
                 _logger.debug(f"Connected to {self._port}")
             except asyncio.TimeoutError:
                 _logger.error(f"Connection to {self._port} timed out after 10 seconds")
                 raise
             except serial.SerialException as e:
                 _logger.error(f"Serial error connecting to {self._port}: {e.__class__.__name__}: {str(e)}")
                 raise
             except Exception as e:
                 _logger.error(f"Failed to connect to {self._port}: {e.__class__.__name__}: {str(e)}")
                 raise

         async def disconnect(self):
             _logger.debug(f"Disconnecting from {self._port}")
             if self._writer:
                 self._writer.close()
                 try:
                     await asyncio.wait_for(self._writer.wait_closed(), timeout=5)
                     _logger.debug(f"Disconnected from {self._port}")
                 except asyncio.TimeoutError:
                     _logger.error(f"Disconnect from {self._port} timed out")
                 except Exception as e:
                     _logger.error(f"Error disconnecting from {self._port}: {e.__class__.__name__}: {str(e)}")
             self._reader = None
             self._writer = None

         async def write(self, data):
             _logger.debug(f"Writing to {self._port}: {data.hex()}")
             if self._writer:
                 self._writer.write(data)
                 try:
                     await asyncio.wait_for(self._writer.drain(), timeout=5)
                     _logger.debug(f"Write completed to {self._port}")
                 except asyncio.TimeoutError:
                     _logger.error(f"Write to {self._port} timed out")
                 except Exception as e:
                     _logger.error(f"Error writing to {self._port}: {e.__class__.__name__}: {str(e)}")
             else:
                 _logger.error(f"No writer available for {self._port}")

         async def read(self, size=1):
             _logger.debug(f"Reading from {self._port}, size={size}")
             if self._reader:
                 try:
                     data = await asyncio.wait_for(self._reader.read(size), timeout=5)
                     _logger.debug(f"Read from {self._port}: {data.hex()}")
                     return data
                 except asyncio.TimeoutError:
                     _logger.error(f"Read from {self._port} timed out after 5 seconds")
                     return bytearray()
                 except Exception as e:
                     _logger.error(f"Error reading from {self._port}: {e.__class__.__name__}: {str(e)}")
                     return bytearray()
             _logger.debug("No reader available, returning empty bytearray")
             return bytearray()