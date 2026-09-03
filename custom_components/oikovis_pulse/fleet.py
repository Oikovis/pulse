"""Assemble units and cells from source entities, notes and stored identity."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .battery_notes import pick_primary_cell
from .classification import classify
from .discovery import filter_candidates, group_into_cells, resolve_reading
from .model import BatteryNote, Cell, CellClass, CellMetadata, SourceEntity, Unit
from .store import StoredCell, new_cell_id, resolve_cell_id
from .suspicions import flag_suspicions

DEFAULT_LOW_THRESHOLD = 20.0

CHARGING_MARKERS = (
    "rechargeable",
    "li-ion",
    "lion",
    "lipo",
    "nimh",
    "nicd",
    "18650",
    "built in",
    "built-in",
)


def _is_charging(battery_type: str | None) -> bool:
    """A rechargeable cell is charged, never replaced.

    Battery Notes' battery_type is free text (e.g. "Li-ion", "18650", "NiMH"),
    not a fixed vocabulary, so this matches known rechargeable markers as a
    substring rather than requiring an exact "rechargeable" value.
    """
    if not battery_type:
        return False
    normalised = battery_type.strip().lower()
    return any(marker in normalised for marker in CHARGING_MARKERS)


@dataclass(frozen=True)
class UnitMeta:
    """Display facts about a unit, resolved from the device and area registries."""

    name: str
    area_id: str | None


def _unit_key(entity: SourceEntity) -> str:
    return entity.device_id if entity.device_id else f"orphan:{entity.entity_id}"


@dataclass
class _PendingCell:
    """A cell whose members are known but whose final identity is not yet claimed."""

    unit_key: str
    unique_ids: list[str]
    members: list[SourceEntity]
    candidate_id: str | None


def _assign_cell_ids(
    pending: list[_PendingCell],
    stored_by_id: Mapping[str, StoredCell],
) -> list[str]:
    """Resolve final cell ids, ensuring a stored id is claimed by at most one cell.

    Several freshly computed cells can independently resolve to the same
    stored cell id (e.g. a stored cell held members {a, b} and this rebuild
    split them into separate cells {a} and {b}). Only one cell may keep that
    identity — the one with the highest overlap against the stored cell's
    member set, tie-broken by the lexicographically smallest sorted member
    unique_ids. Every other claimant gets a fresh id.
    """
    claims: dict[str, list[int]] = {}
    for index, cell in enumerate(pending):
        if cell.candidate_id is not None:
            claims.setdefault(cell.candidate_id, []).append(index)

    final_ids: list[str | None] = [cell.candidate_id for cell in pending]

    for candidate_id, indices in claims.items():
        if len(indices) == 1:
            continue

        stored_members = set(stored_by_id[candidate_id].member_unique_ids)

        def sort_key(
            i: int, stored_members: frozenset[str] = frozenset(stored_members)
        ) -> tuple[int, tuple[str, ...]]:
            overlap = len(set(pending[i].unique_ids) & stored_members)
            return (-overlap, tuple(sorted(pending[i].unique_ids)))

        ordered = sorted(indices, key=sort_key)
        winner = ordered[0]
        for loser in ordered[1:]:
            final_ids[loser] = None

        final_ids[winner] = candidate_id

    return [cid if cid is not None else new_cell_id() for cid in final_ids]


def build_fleet(
    entities: Sequence[SourceEntity],
    notes: Sequence[BatteryNote],
    units_meta: Mapping[str, UnitMeta],
    stored: Sequence[StoredCell],
    default_low_threshold: float = DEFAULT_LOW_THRESHOLD,
) -> list[Unit]:
    """Build the fleet. Pure: no Home Assistant objects cross this boundary."""
    candidates = filter_candidates(entities)

    by_unit: dict[str, list[SourceEntity]] = {}
    for entity in candidates:
        by_unit.setdefault(_unit_key(entity), []).append(entity)

    entity_notes = {n.source_entity_id: n for n in notes if n.source_entity_id}
    device_notes = {n.device_id: n for n in notes if n.device_id and not n.source_entity_id}
    overrides = {s.cell_id: s.class_override for s in stored}
    stored_by_id = {s.cell_id: s for s in stored}

    # Pass 1: group every unit's entities into cells and compute each cell's
    # candidate stored identity, without yet committing to it.
    unit_order: list[str] = []
    unit_groups: dict[str, list[list[SourceEntity]]] = {}
    pending: list[_PendingCell] = []
    pending_index_by_group: dict[tuple[str, int], int] = {}

    for unit_key, unit_entities in by_unit.items():
        unit_order.append(unit_key)
        groups = group_into_cells(unit_entities, notes)
        unit_groups[unit_key] = groups
        for group_index, members in enumerate(groups):
            unique_ids = [m.unique_id for m in members]
            candidate_id = resolve_cell_id(unique_ids, stored)
            pending_index_by_group[(unit_key, group_index)] = len(pending)
            pending.append(
                _PendingCell(
                    unit_key=unit_key,
                    unique_ids=unique_ids,
                    members=list(members),
                    candidate_id=candidate_id,
                )
            )

    # Pass 2: resolve collisions fleet-wide so a stored id is claimed once.
    final_ids = _assign_cell_ids(pending, stored_by_id)

    # Pass 3: build the actual units and cells using the resolved identities.
    units: list[Unit] = []
    for unit_key in unit_order:
        unit_entities = by_unit[unit_key]
        meta = units_meta.get(unit_key)
        name = meta.name if meta else unit_entities[0].entity_id.split(".", 1)[-1]
        area_id = meta.area_id if meta else None

        groups = unit_groups[unit_key]
        cells: list[Cell] = []
        members_by_cell: dict[str, list[SourceEntity]] = {}

        for group_index, members in enumerate(groups):
            pending_cell = pending[pending_index_by_group[(unit_key, group_index)]]
            cell_id = final_ids[pending_index_by_group[(unit_key, group_index)]]
            unique_ids = pending_cell.unique_ids
            kind, percentage, low, critical = resolve_reading(members)

            note = next(
                (entity_notes[m.entity_id] for m in members if m.entity_id in entity_notes),
                None,
            )
            metadata = CellMetadata(low_threshold=default_low_threshold)
            if note is not None:
                metadata.battery_type = note.battery_type
                metadata.battery_quantity = note.battery_quantity
                metadata.last_replaced = note.last_replaced
                metadata.bn_low_threshold = note.low_threshold

            override_raw = overrides.get(cell_id)
            override = CellClass(override_raw) if override_raw else None

            charging = _is_charging(metadata.battery_type)

            cell = Cell(
                cell_id=cell_id,
                members=tuple(unique_ids),
                reading_kind=kind,
                percentage=percentage,
                low=low,
                critical=critical,
                charging=charging,
                cell_class=classify(members, override),
                metadata=metadata,
            )
            cells.append(cell)
            members_by_cell[cell_id] = list(members)

        unresolved = False
        device_note = device_notes.get(unit_key)
        if device_note is not None:
            primary_id = pick_primary_cell(cells, members_by_cell, name)
            if primary_id is None:
                unresolved = True
            else:
                for cell in cells:
                    if cell.cell_id != primary_id:
                        continue
                    if cell.metadata.battery_type is None:
                        cell.metadata.battery_type = device_note.battery_type
                        cell.metadata.battery_quantity = device_note.battery_quantity
                        cell.metadata.last_replaced = device_note.last_replaced
                        cell.metadata.bn_low_threshold = device_note.low_threshold
                    cell.charging = _is_charging(cell.metadata.battery_type)

        units.append(
            Unit(
                unit_id=unit_key,
                name=name,
                area_id=area_id,
                cells=cells,
                unresolved_note=unresolved,
            )
        )

    flag_suspicions(units)
    return units
