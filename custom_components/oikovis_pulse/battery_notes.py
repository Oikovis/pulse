"""Battery Notes integration: metadata mining and write-back."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .discovery import name_stem, normalise_name
from .model import BatteryNote, Cell, SourceEntity

DOMAIN_BATTERY_NOTES = "battery_notes"
SERVICE_SET_BATTERY_REPLACED = "set_battery_replaced"

# Battery Notes writes a timestamp back with a one-microsecond offset.
# Comparisons must tolerate it; never compare for equality.
TIMESTAMP_TOLERANCE_SECONDS = 1.0


def parse_note(attributes: Mapping[str, Any], device_id: str | None) -> BatteryNote:
    """Build a BatteryNote from a Battery Notes entity's state attributes."""
    source = attributes.get("source_entity_id") or None
    quantity = attributes.get("battery_quantity")
    try:
        quantity_value = int(quantity) if quantity is not None else None
    except (TypeError, ValueError):
        quantity_value = None

    threshold = attributes.get("battery_low_threshold")
    try:
        threshold_value = float(threshold) if threshold is not None else None
    except (TypeError, ValueError):
        threshold_value = None

    return BatteryNote(
        source_entity_id=source,
        device_id=attributes.get("device_id") or device_id,
        battery_type=attributes.get("battery_type") or None,
        battery_quantity=quantity_value,
        low_threshold=threshold_value,
        last_replaced=attributes.get("battery_last_replaced") or None,
    )


def pick_primary_cell(
    cells: Sequence[Cell],
    members_by_cell: Mapping[str, Sequence[SourceEntity]],
    device_name: str,
) -> str | None:
    """Return the cell a device-level note describes, or None when ambiguous.

    Guessing wrong sends someone to the shop for the wrong battery, so an
    ambiguous device yields no primary cell and the note is surfaced as
    unresolved instead.

    Matching algorithm:
    1. If the unit has exactly one cell, return it. A single cell is
       unambiguous by definition, regardless of whether it has a percentage
       reading.
    2. Filter to cells with percentage members.
    3. If exactly one such cell, return it.
    4. Find candidates: cells whose stem has a prefix relationship with the
       normalised device name (one startswith the other).
    5. If exactly one candidate, return it.
    6. If multiple candidates, prefer the one with the smallest mismatch
       (characters in one that aren't in the other).
    7. If multiple candidates share the smallest mismatch, return None (ambiguous).
    8. If no candidates, return None.
    """
    if len(cells) == 1:
        return cells[0].cell_id

    percentage_cells = [
        cell
        for cell in cells
        if any(member.unit == "%" for member in members_by_cell.get(cell.cell_id, ()))
    ]
    if not percentage_cells:
        return None
    if len(percentage_cells) == 1:
        return percentage_cells[0].cell_id

    target = normalise_name(device_name)
    if not target:
        # A device name that normalises to nothing gives no signal to match
        # against; refuse to guess rather than pick an arbitrary cell.
        return None
    candidates: list[tuple[int, str]] = []  # (mismatch_distance, cell_id)

    for cell in percentage_cells:
        for member in members_by_cell.get(cell.cell_id, ()):
            stem = name_stem(member.entity_id)
            if stem.startswith(target):
                # stem is longer; mismatch is the extra characters in stem
                mismatch = len(stem) - len(target)
                candidates.append((mismatch, cell.cell_id))
                break
            elif target.startswith(stem):
                # target is longer; mismatch is the extra characters in target
                mismatch = len(target) - len(stem)
                candidates.append((mismatch, cell.cell_id))
                break

    if not candidates:
        return None

    min_mismatch = min(c[0] for c in candidates)
    best = [c[1] for c in candidates if c[0] == min_mismatch]

    if len(best) == 1:
        return best[0]
    return None
