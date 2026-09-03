"""Coordinator assembling the Pulse fleet from Home Assistant registries."""

from __future__ import annotations

import dataclasses
import logging
from datetime import timedelta

import homeassistant.util.dt as dt_util
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

_STORED_CELL_FIELDS = {f.name for f in dataclasses.fields(StoredCell)}
_STORED_CELL_REQUIRED = {
    f.name
    for f in dataclasses.fields(StoredCell)
    if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
}


class PulseCoordinator(DataUpdateCoordinator[list[Unit]]):
    """Rebuild the fleet on a timer. Registry-change-driven rebuilds are not
    yet wired up; only the timed refresh triggers ``_async_update_data``.
    """

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
        """Load persisted cell identity.

        Loading must never hard-fail setup: a store written by a later
        version (extra keys), a store missing a required field, or an
        entirely malformed payload all degrade to "skip the bad record" or
        "start empty" rather than raising, so a corrupt or forward-written
        store file cannot lock the user out of the integration.
        """
        try:
            raw = await self._store.async_load() or {}
            raw_cells = raw.get("cells", []) if isinstance(raw, dict) else []
        except Exception:
            _LOGGER.warning("Failed to load %s store; starting with no stored cells", STORAGE_KEY)
            self._stored = []
            return

        cells: list[StoredCell] = []
        for item in raw_cells:
            if not isinstance(item, dict):
                _LOGGER.warning("Skipping stored cell record that is not an object: %r", item)
                continue
            if not _STORED_CELL_REQUIRED.issubset(item):
                _LOGGER.warning("Skipping stored cell record missing required field(s): %r", item)
                continue
            known = {key: value for key, value in item.items() if key in _STORED_CELL_FIELDS}
            try:
                cells.append(StoredCell(**known))
            except TypeError:
                _LOGGER.warning("Skipping unusable stored cell record: %r", item)
                continue
        self._stored = cells

    async def async_save_store(self, units: list[Unit]) -> None:
        """Persist cell identity and overrides.

        A stored cell absent from the fresh fleet is retained (never
        deleted here) and gets ``gone_since`` set once, the first time it
        goes missing; an existing ``gone_since`` is never overwritten, and a
        cell that reappears has it cleared again. Metadata and
        ``class_override`` for a gone cell are left untouched.
        """
        existing = {cell.cell_id: cell for cell in self._stored}
        seen_ids: set[str] = set()
        for unit in units:
            for cell in unit.cells:
                seen_ids.add(cell.cell_id)
                record = existing.get(cell.cell_id)
                if record is None:
                    record = StoredCell(cell_id=cell.cell_id)
                    existing[cell.cell_id] = record
                record.member_unique_ids = list(cell.members)
                record.gone_since = None

        now_iso = dt_util.utcnow().isoformat()
        for cell_id, record in existing.items():
            if cell_id in seen_ids:
                continue
            if record.gone_since is None:
                record.gone_since = now_iso

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
