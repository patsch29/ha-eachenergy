"""Diagnostics support: raw (anonymised) inverter answers for bug reports."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import CONF_LOGGER_SERIAL

TO_REDACT = {CONF_HOST, CONF_LOGGER_SERIAL, "serial", "unique_id"}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    return {
        "entry": async_redact_data({"data": dict(entry.data), "options": dict(entry.options)}, TO_REDACT),
        "device": async_redact_data(dict(coordinator.info), TO_REDACT),
        "last_update_success": coordinator.last_update_success,
        # Query answers only (command 0x01 with the serial number is never stored here)
        "frames": {f"0x{cmd:02x}": frame.hex(" ") for cmd, frame in sorted(data.items())},
    }
