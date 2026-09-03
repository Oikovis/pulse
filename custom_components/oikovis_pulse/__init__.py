"""Oikovis Pulse integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import PulseCoordinator
from .panel import async_register, async_unregister
from .websocket import async_register_websocket

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pulse from a config entry."""
    coordinator = PulseCoordinator(hass)
    await coordinator.async_load_store()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {DATA_COORDINATOR: coordinator}

    await async_register(hass)
    async_register_websocket(hass)
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Tear down the panel and forget the entry."""
    await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR])
    await async_unregister(hass)
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
