"""Pure discovery logic: filtering, grouping, reading resolution."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from .model import BatteryNote, ReadingKind, SourceEntity

BATTERY_DEVICE_CLASS = "battery"

_NUMERIC_SUFFIX = re.compile(r"_\d+$")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
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
    """Reduce a display name to a comparable key. Shared by every name comparison."""
    return _NON_ALNUM.sub("_", text.strip().lower()).strip("_")


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
CRITICAL_MARKERS = ("critical",)


def _usable(entity: SourceEntity) -> bool:
    return entity.state.strip().lower() not in UNUSABLE_STATES


def _as_float(state: str) -> float | None:
    try:
        return float(state)
    except (TypeError, ValueError):
        return None


def resolve_reading(
    members: Sequence[SourceEntity],
) -> tuple[ReadingKind, float | None, bool, bool]:
    """Resolve a cell's reading from its usable members.

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
            if any(marker in member.entity_id for marker in CRITICAL_MARKERS):
                critical = True
            else:
                low = True

    if percentage is not None:
        return ReadingKind.PERCENTAGE, percentage, low, critical
    if has_usable_flag:
        return ReadingKind.BINARY, None, low, critical
    return ReadingKind.NONE, None, False, False
