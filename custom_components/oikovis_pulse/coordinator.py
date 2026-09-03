"""Coordinator assembling the Pulse fleet from Home Assistant registries."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .adapter import entity_to_dto
from .battery_notes import DOMAIN_BATTERY_NOTES, parse_note
from .fleet import UnitMeta, build_fleet
from .model import Unit
from .store import STORAGE_KEY, STORAGE_VERSION, StoredCell

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=5)


class PulseCoordinator(DataUpdateCoordinator[list[Unit]]):
    """Rebuild the fleet on a timer and on registry changes."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Oikovis Pulse",
            update_interval=UPDATE_INTERVAL,
        )
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._stored: list[StoredCell] = []

    async def async_load_store(self) -> None:
        """Load persisted cell identity."""
        raw = await self._store.async_load() or {}
        self._stored = [StoredCell(**item) for item in raw.get("cells", [])]

    async def async_save_store(self, units: list[Unit]) -> None:
        """Persist cell identity and overrides."""
        existing = {cell.cell_id: cell for cell in self._stored}
        for unit in units:
            for cell in unit.cells:
                record = existing.get(cell.cell_id)
                if record is None:
                    record = StoredCell(cell_id=cell.cell_id)
                    existing[cell.cell_id] = record
                record.member_unique_ids = list(cell.members)
                record.gone_since = None
        self._stored = list(existing.values())
        await self._store.async_save({"cells": [vars(cell) for cell in self._stored]})

    async def _async_update_data(self) -> list[Unit]:
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)
        ar.async_get(self.hass)

        dtos = []
        notes = []
        for entry in entity_registry.entities.values():
            state = self.hass.states.get(entry.entity_id)
            if entry.platform == DOMAIN_BATTERY_NOTES:
                if state is not None and state.attributes.get("battery_type") is not None:
                    notes.append(parse_note(state.attributes, entry.device_id))
                continue
            dto = entity_to_dto(entry, state)
            if dto is not None:
                dtos.append(dto)

        units_meta: dict[str, UnitMeta] = {}
        for device in device_registry.devices.values():
            units_meta[device.id] = UnitMeta(
                name=device.name_by_user or device.name or device.id,
                area_id=device.area_id,
            )

        units = build_fleet(dtos, notes, units_meta, self._stored)
        await self.async_save_store(units)
        return units
