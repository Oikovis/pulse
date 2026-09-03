"""Summary sensors. Pulse creates no per-cell entities."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import PulseCoordinator
from .websocket import summarise

SUMMARY_KEYS = (
    "cells_low",
    "cells_critical",
    "cells_without_reading",
    "cells_needing_attention",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the four summary sensors."""
    coordinator: PulseCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(PulseSummarySensor(coordinator, key) for key in SUMMARY_KEYS)


class PulseSummarySensor(CoordinatorEntity[PulseCoordinator], SensorEntity):
    """One published count over the whole fleet."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: PulseCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_name = key.replace("_", " ").capitalize()

    @property
    def native_value(self) -> int:
        """Return the current count."""
        return summarise(self.coordinator.data or [])[self._key]
