"""Pure discovery logic: filtering, grouping, reading resolution."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from .model import BatteryNote, ReadingKind, SourceEntity

BATTERY_DEVICE_CLASS = "battery"

_NUMERIC_SUFFIX = re.compile(r"_\d+$")
_NON_WORD = re.compile(r"[^\w]+", flags=re.UNICODE)
_BATTERY_SUFFIXES = (
    "_battery_critical",
    "_battery_level",
    "_battery_state",
    "_battery_low",
    "_low_battery",
    "_battery",
    "_batt",
)


def filter_candidates(
    entities: Iterable[SourceEntity],
    *,
    battery_notes_platform: str = "battery_notes",
) -> list[SourceEntity]:
    """Return only entities that can source a cell.

    Battery Notes entities are mirrors of other entities, not batteries of
    their own. They are recognised by their platform, never by name: a mirror's
    object id is built from its source's full name, so name matching produces a
    stem that does not match its own source.
    """
    return [
        entity
        for entity in entities
        if entity.device_class == BATTERY_DEVICE_CLASS
        and entity.platform != battery_notes_platform
        and not entity.disabled
        and not entity.hidden
    ]


def normalise_name(text: str) -> str:
    """Reduce a display name to a comparable key. Shared by every name comparison.

    Unicode-aware: uses casefold() and a Unicode word-character class so
    non-Latin names (Greek, Cyrillic, accented Latin, ...) normalise to a
    meaningful, non-empty key instead of collapsing to the empty string.
    """
    return _NON_WORD.sub("_", text.strip().casefold()).strip("_")


def name_stem(entity_id: str) -> str:
    """Reduce an entity id to the name of the thing whose battery it describes."""
    object_id = entity_id.split(".", 1)[-1]
    object_id = _NUMERIC_SUFFIX.sub("", object_id)
    for suffix in _BATTERY_SUFFIXES:
        if object_id.endswith(suffix):
            object_id = object_id[: -len(suffix)]
            break
    return object_id


def group_into_cells(
    entities: Sequence[SourceEntity],
    notes: Sequence[BatteryNote] = (),
) -> list[list[SourceEntity]]:
    """Group a unit's entities into cells, one list of members per cell.

    An entity named by an entity-level Battery Notes note is explicit truth and
    forms its own cell. Everything else is grouped by name stem, which is the
    only signal available inside a device and the weakest part of this design.
    """
    declared = {note.source_entity_id for note in notes if note.source_entity_id}

    cells: list[list[SourceEntity]] = []
    by_stem: dict[str, list[SourceEntity]] = {}

    for entity in entities:
        if entity.entity_id in declared:
            cells.append([entity])
            continue
        by_stem.setdefault(name_stem(entity.entity_id), []).append(entity)

    cells.extend(by_stem.values())
    return cells


UNUSABLE_STATES = frozenset({"unavailable", "unknown", "none", ""})


def _usable(entity: SourceEntity) -> bool:
    return entity.state.strip().lower() not in UNUSABLE_STATES


def _as_float(state: str) -> float | None:
    try:
        return float(state)
    except (TypeError, ValueError):
        return None


def _is_critical_flag(entity_id: str) -> bool:
    """Check if a flag entity is a critical-level flag, not a low-level flag.

    Classification is based on the entity ID's object part ending with
    _battery_critical (after stripping Home Assistant duplicate-id digits).
    This avoids false positives from device names containing "critical".
    """
    object_id = entity_id.split(".", 1)[-1]
    object_id = _NUMERIC_SUFFIX.sub("", object_id)
    return object_id.endswith("_battery_critical")


def resolve_reading(
    members: Sequence[SourceEntity],
) -> tuple[ReadingKind, float | None, bool, bool]:
    """Resolve a cell's reading from its usable members.

    Returns (kind, percentage, low, critical) where:
    - kind: PERCENTAGE if any percentage is usable, else BINARY if any flag is
      usable, else NONE
    - percentage: the first usable percentage value, or None. Percentages are
      not clamped; values like -5 or 150 are accepted as-is. Precedence follows
      members order; callers must supply a stable order.
    - low, critical: flags representing usable on-state flags. When both
      percentage and critical flag are usable, the flag wins for alerting and
      the percentage wins for display — both are returned.

    Priority is decided by usable state, never by declared unit: a percentage
    sensor sitting at `unavailable` must not stop a healthy low-battery flag
    beside it from being read.
    """
    percentage: float | None = None
    low = False
    critical = False
    has_usable_flag = False

    for member in members:
        if not _usable(member):
            continue
        if member.unit == "%":
            value = _as_float(member.state)
            if value is not None and percentage is None:
                percentage = value
            continue
        has_usable_flag = True
        if member.state.strip().lower() == "on":
            if _is_critical_flag(member.entity_id):
                critical = True
            else:
                low = True

    if percentage is not None:
        return ReadingKind.PERCENTAGE, percentage, low, critical
    if has_usable_flag:
        return ReadingKind.BINARY, None, low, critical
    return ReadingKind.NONE, None, False, False
