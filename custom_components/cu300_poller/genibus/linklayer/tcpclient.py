import logging
import asyncio
from .connection import Connection

_logger = logging.getLogger(__name__)

class TcpClient(Connection):
    def __init__(self, host, port):
        super().__init__()
        self._host = host
        self._port = port
        self._reader = None
        self._writer = None

    async def connect(self):
        try:
            self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
        except Exception as e:
            _logger.error(f"Failed to connect to {self._host}:{self._port}: {e}")
            raise

    async def disconnect(self):
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._reader = None
        self._writer = None

    async def write(self, data):
        if self._writer:
            self._writer.write(data)
            await self._writer.drain()

    async def read(self, size=1):
        if self._reader:
            return await self._reader.read(size)
        return bytearray()