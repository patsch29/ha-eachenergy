"""Each Energy hybrid inverter (local, via SOLARMAN stick logger)."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ADDRESS,
    CONF_LOGGER_SERIAL,
    CONF_SCAN_INTERVAL,
    DEFAULT_ADDRESS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    POLL_COMMANDS,
)
from .protocol import EachEnergyClient, EachEnergyError

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


class EachEnergyCoordinator(DataUpdateCoordinator[dict[int, bytes]]):
    """Polls all query commands of the inverter."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: EachEnergyClient) -> None:
        interval = entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self.info: dict = {}

    async def _async_update_data(self) -> dict[int, bytes]:
        if not self.info:
            try:
                self.info = await self.client.device_info()
            except EachEnergyError as err:
                raise UpdateFailed(str(err)) from err
        result: dict[int, bytes] = {}
        errors: list[str] = []
        for cmd in POLL_COMMANDS:
            try:
                result[cmd] = await self.client.query(cmd)
            except EachEnergyError as err:
                errors.append(str(err))
        if not result:
            raise UpdateFailed("; ".join(errors) or "no data")
        if errors:
            _LOGGER.debug("Partial update: %s", errors)
        return result


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = EachEnergyClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_LOGGER_SERIAL],
        entry.data.get(CONF_ADDRESS, DEFAULT_ADDRESS),
    )
    coordinator = EachEnergyCoordinator(hass, entry, client)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await client.close()
        raise
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.close()
    return unloaded
