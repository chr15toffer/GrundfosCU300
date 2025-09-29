"""Base connection class for GENIBus communication."""
import abc
import asyncio

class Connection(metaclass=abc.ABCMeta):
    """Abstract base class for GENIBus connections."""

    def __init__(self):
        self._reader = None
        self._writer = None

    @abc.abstractmethod
    async def connect(self):
        """Establish connection to the device."""
        pass

    @abc.abstractmethod
    async def disconnect(self):
        """Close connection to the device."""
        pass

    @abc.abstractmethod
    async def write(self, data):
        """Write data to the device."""
        pass

    @abc.abstractmethod
    async def read(self, size=1):
        """Read data from the device."""
        pass