"""Flag units that look related. Flags only: Pulse never merges on a guess."""

from __future__ import annotations

from .discovery import normalise_name
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
    by_key: dict[str, Unit] = {}
    for unit in units:
        key = _key(unit.name)
        first = by_key.get(key)
        if first is None:
            by_key[key] = unit
            continue
        if _same_shape(first, unit):
            unit.duplicate_of = first.unit_id

    dead = [
        u for u in units if u.cells and all(c.reading_kind is ReadingKind.NONE for c in u.cells)
    ]
    orphans = {
        _key(u.name): u
        for u in units
        if u.unit_id.startswith("orphan:")
        and any(c.reading_kind is not ReadingKind.NONE for c in u.cells)
    }
    for unit in dead:
        target = _key(unit.name)
        for orphan_key, orphan in orphans.items():
            if orphan_key.startswith(target) or target.startswith(orphan_key):
                unit.link_candidate = orphan.unit_id
                break


def _same_shape(left: Unit, right: Unit) -> bool:
    if len(left.cells) != len(right.cells):
        return False
    for a, b in zip(left.cells, right.cells, strict=False):
        if a.metadata.battery_type != b.metadata.battery_type:
            return False
        if a.percentage != b.percentage:
            return False
    return True
