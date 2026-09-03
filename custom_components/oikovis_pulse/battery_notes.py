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
    """
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
    exact = [
        cell
        for cell in percentage_cells
        if any(
            name_stem(member.entity_id) == target
            for member in members_by_cell.get(cell.cell_id, ())
        )
    ]
    if len(exact) == 1:
        return exact[0].cell_id
    return None
