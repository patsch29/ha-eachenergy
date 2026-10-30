"""Constants for the Each Energy integration."""

DOMAIN = "eachenergy"

CONF_LOGGER_SERIAL = "logger_serial"
CONF_ADDRESS = "address"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 8899
DEFAULT_ADDRESS = 1
DEFAULT_SCAN_INTERVAL = 15

# Commands polled every cycle (all read-only, function code 0x01)
POLL_COMMANDS = (0x02, 0x03, 0x34, 0x36, 0x09, 0xB0, 0xB1, 0x08, 0x0A, 0xB5)
