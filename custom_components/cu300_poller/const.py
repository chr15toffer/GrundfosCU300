"""Constants for CU300 Poller integration."""

DOMAIN = "cu300_poller"

# Connection types
CONNECTION_TYPE_SERIAL = "serial"
CONNECTION_TYPE_TCP = "tcp"

# Configuration keys
CONF_UPDATE_INTERVAL = "update_interval"
CONF_DEVICE_ADDRESS = "device_address"
CONF_SOURCE_ADDRESS = "source_address"

# Default values
DEFAULT_UPDATE_INTERVAL = 30  # seconds
DEFAULT_DEVICE_ADDRESS = 0x20
DEFAULT_SOURCE_ADDRESS = 0x04
DEFAULT_TCP_PORT = 502

# Attributes
ATTR_REFERENCE = "reference"
