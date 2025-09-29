"""Custom exceptions for GENIBus protocol."""


class GENIBusError(Exception):
    """Base exception for GENIBus errors."""


class ConnectionError(GENIBusError):
    """Raised when connection fails or is lost."""


class ProtocolError(GENIBusError):
    """Raised when protocol communication fails."""


class CRCError(ProtocolError):
    """Raised when CRC check fails."""


class TimeoutError(GENIBusError):
    """Raised when operation times out."""


class InvalidFrameError(ProtocolError):
    """Raised when frame structure is invalid."""


class DeviceError(GENIBusError):
    """Raised when device returns an error."""
