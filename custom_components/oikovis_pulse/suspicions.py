"""Flag units that look related. Flags only: Pulse never merges on a guess."""

from __future__ import annotations

from .discovery import name_stem, normalise_name
from .model import ReadingKind, Unit

_LEADING_QUALIFIERS = ("select", "copy of", "new")


def _key(name: str) -> str:
    """Normalise a unit name, ignoring qualifiers integrations prepend."""
    text = name.strip().lower()
    for qualifier in _LEADING_QUALIFIERS:
        if text.startswith(f"{qualifier} "):
            text = text[len(qualifier) + 1 :]
    return normalise_name(text)


def flag_suspicions(units: list[Unit]) -> None:
    """Set duplicate_of and link_candidate in place.

    A false merge hides a real battery, so nothing here acts: it only marks
    what a person should be asked about.
    """
    # Find duplicates: units with the same normalised name and same shape.
    # Group by name key, then within each group, determine which unit is the
    # deterministic reference (smallest unit_id), and flag all others against it.
    by_key: dict[str, list[Unit]] = {}
    for unit in units:
        key = _key(unit.name)
        by_key.setdefault(key, []).append(unit)

    for _name_key, group in by_key.items():
        if len(group) < 2:
            continue
        # Sort by unit_id to get a deterministic order.
        group.sort(key=lambda u: u.unit_id)
        reference = group[0]
        for candidate in group[1:]:
            if _same_shape(reference, candidate):
                candidate.duplicate_of = reference.unit_id

    # Find link candidates: dead units paired with orphan entities whose names match.
    dead = [
        u for u in units if u.cells and all(c.reading_kind is ReadingKind.NONE for c in u.cells)
    ]
    orphans = {
        normalise_name(name_stem(u.unit_id[len("orphan:") :])): u
        for u in units
        if u.unit_id.startswith("orphan:")
        and any(c.reading_kind is not ReadingKind.NONE for c in u.cells)
    }
    for unit in dead:
        target = _key(unit.name)
        # A dead unit can link to an orphan only if their normalised names are
        # exactly equal (no substring containment).
        if target in orphans:
            orphan = orphans[target]
            # Prevent self-linking: unit can never be its own link_candidate.
            if unit.unit_id != orphan.unit_id:
                unit.link_candidate = orphan.unit_id


def _same_shape(left: Unit, right: Unit) -> bool:
    """Check if two units have the same cell structure (order-insensitive).

    Two units have the same shape if they have the same number of cells,
    and those cells can be paired such that each pair has matching battery_type
    and percentage. Order is ignored: cells are compared as unordered sets.
    """
    if len(left.cells) != len(right.cells):
        return False
    # Build a sorted tuple of (battery_type, percentage) for each unit.
    # This makes the comparison order-insensitive.
    left_signature = sorted((c.metadata.battery_type, c.percentage) for c in left.cells)
    right_signature = sorted((c.metadata.battery_type, c.percentage) for c in right.cells)
    return left_signature == right_signature
