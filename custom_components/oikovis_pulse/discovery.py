"""Pure discovery logic: filtering, grouping, reading resolution."""

from __future__ import annotations

from collections.abc import Iterable

from .model import SourceEntity

BATTERY_DEVICE_CLASS = "battery"


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
