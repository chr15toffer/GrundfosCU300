     """Main polling logic for CU300 using GENIBus library."""
     import asyncio
     import logging
     from .genibus.linklayer.serialport import SerialPort
     from .genibus.linklayer.tcpclient import TcpClient
     from .genibus.apdu import APDU
     from .genibus import gbdefs as gbdefs
     from .genibus.utils import crc

     _LOGGER = logging.getLogger(__name__)

     class CU300Poller:
         def __init__(self, connection_type, host=None, port=None):
             self._connection_type = connection_type
             self._host = host
             self._port = port
             self._connection = None
             self._data = {}  # Store polled data (e.g., {'head': 10.5, 'flow': 2.0, ...})
             self._lock = asyncio.Lock()
             _LOGGER.debug(f"Initialized CU300Poller with type={connection_type}, host={host}, port={port}")

         async def connect(self):
             """Connect to the device."""
             _LOGGER.debug(f"Attempting to connect to {self._port or self._host} with type {self._connection_type}")
             try:
                 if self._connection_type == "tcp":
                     self._connection = TcpClient(self._host, self._port)
                     _LOGGER.debug("Created TcpClient instance")
                 else:
                     self._connection = SerialPort(self._port)
                     _LOGGER.debug("Created SerialPort instance")
                 await asyncio.wait_for(self._connection.connect(), timeout=10)
                 _LOGGER.debug("Connection established")
                 # Send connect request (from library examples)
                 connect_req = bytearray([0x27, 0x0e, 0xfe, 0x01, 0x00, 0x02, 0x02, 0x03, 0x04, 0x02, 0x2e, 0x2f, 0x02, 0x02, 0x94, 0x95, 0xa2, 0xaa])
                 response = await asyncio.wait_for(self._send(connect_req), timeout=5)
                 _LOGGER.debug(f"Connect request sent, response: {response.hex()}")
             except asyncio.TimeoutError:
                 _LOGGER.error(f"Connection to {self._port or self._host} timed out")
                 raise
             except Exception as e:
                 _LOGGER.error(f"Failed to connect to {self._port or self._host}: {e.__class__.__name__}: {str(e)}")
                 raise

         async def disconnect(self):
             """Disconnect from the device."""
             _LOGGER.debug("Disconnecting from device")
             if self._connection:
                 await self._connection.disconnect()
                 _LOGGER.debug("Disconnected")

         async def poll(self):
             """Poll for data (measured values from DATA_REQ in library)."""
             _LOGGER.debug("Starting poll")
             async with self._lock:
                 # Example DATA_REQ from library
                 data_req = bytearray([0x27, 0x1E, 0x20, 0x04, 0x02, 0x1A, 0x51, 0x52, 0x53, 0x2F, 0x30, 0x31, 0x3D, 0x3E, 0x25, 0x27, 0x2C, 0x2B, 0x18, 0x19, 0x5A, 0x22, 0x98, 0x99, 0x23, 0x61, 0x9E, 0x9F, 0xA0, 0xA1, 0xA2, 0xA3, 0x11, 0x76])
                 response = await asyncio.wait_for(self._send(data_req), timeout=5)
                 _LOGGER.debug(f"Poll response: {response.hex()}")
                 if response and crc.check_tel(response):
                     # Parse response (simplified; adapt from apdu.py in library)
                     apdu = APDU.from_bytes(response)
                     self._data['act_mode1'] = apdu.get_value('act_mode1')  # Example parsing
                     self._data['head'] = apdu.get_value('h')  # Head (pressure)
                     self._data['flow'] = apdu.get_value('q')  # Flow
                     self._data['speed'] = apdu.get_value('speed')
                     self._data['alarm_code'] = apdu.get_value('alarm_code')
                     _LOGGER.debug(f"Parsed data: {self._data}")
                 else:
                     _LOGGER.error("Invalid response or CRC error")

         async def _send(self, frame):
             """Send frame and get response."""
             _LOGGER.debug(f"Sending frame: {frame.hex()}")
             frame = crc.append_tel(frame)
             await self._connection.write(frame)
             response = await self._connection.read()
             _LOGGER.debug(f"Received response: {response.hex()}")
             return response

         async def start_pump(self, call):
             """Service to start pump (from REF_REQ example)."""
             _LOGGER.debug("Starting pump")
             start_cmd = bytearray([0x27, 0x09, 0x20, 0x04, 0x03, 0x81, 0x06, 0x05, 0x82, 0x01, 0xA5, 0x28, 0xDF])
             await asyncio.wait_for(self._send(start_cmd), timeout=5)

         async def stop_pump(self, call):
             """Service to stop pump."""
             _LOGGER.debug("Stopping pump")
             stop_cmd = bytearray([0x27, 0x09, 0x20, 0x04, 0x03, 0x81, 0x07, 0x05, 0x82, 0x01, 0x00, 0x28, 0xDF])
             await asyncio.wait_for(self._send(stop_cmd), timeout=5)

         async def set_reference(self, call):
             """Service to set reference value."""
             ref_value = call.data.get('reference', 50)  # Default 50%
             _LOGGER.debug(f"Setting reference to {ref_value}")
             set_ref = bytearray([0x27, 0x09, 0x20, 0x04, 0x05, 0x82, 0x01, ref_value, 0x28, 0xDF])
             await asyncio.wait_for(self._send(set_ref), timeout=5)

         async def test_connection(self, call):
             """Service to test serial connection."""
             _LOGGER.debug(f"Testing connection to {self._port or self._host}")
             try:
                 connect_req = bytearray([0x27, 0x0e, 0xfe, 0x01, 0x00, 0x02, 0x02, 0x03, 0x04, 0x02, 0x2e, 0x2f, 0x02, 0x02, 0x94, 0x95, 0xa2, 0xaa])
                 response = await asyncio.wait_for(self._send(connect_req), timeout=5)
                 _LOGGER.debug(f"Test connection response: {response.hex()}")
                 if response:
                     _LOGGER.info("Connection test successful")
                 else:
                     _LOGGER.warning("No response received from device")
             except asyncio.TimeoutError:
                 _LOGGER.error(f"Connection test to {self._port or self._host} timed out")
             except Exception as e:
                 _LOGGER.error(f"Connection test failed: {e.__class__.__name__}: {str(e)}")

         def get_data(self, key):
             return self._data.get(key)