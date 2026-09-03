"""Persistent state Pulse owns: cell identity, overrides, metadata gaps."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

STORAGE_VERSION = 1
STORAGE_KEY = "oikovis_pulse"

# A reloaded integration must not destroy a battery's replaced-date, so a cell
# whose entities vanish is retained before purge rather than dropped.
GONE_RETENTION_DAYS = 90


@dataclass
class StoredCell:
    """What Pulse persists about one cell."""

    cell_id: str
    member_unique_ids: list[str] = field(default_factory=list)
    class_override: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    gone_since: str | None = None


def new_cell_id() -> str:
    """Mint an identity that no rename or entity id change can invalidate."""
    return uuid.uuid4().hex


def resolve_cell_id(
    member_unique_ids: Sequence[str],
    stored: Sequence[StoredCell],
) -> str | None:
    """Re-resolve a freshly computed cell to its stored identity.

    Matching is by intersection of unique_id sets, never entity ids: renaming a
    device rewrites every entity id at once, and an entity-id identity would
    orphan the cell's replaced-date as a result.

    When multiple stored cells have the same overlap count, the one with the
    lexicographically smallest cell_id wins. This ensures the result is stable
    and independent of the order of the stored list, preventing a persisted
    cell's identity from flipping between restarts and accidentally inheriting
    another cell's replaced-date.
    """
    incoming = set(member_unique_ids)
    if not incoming:
        return None

    best_id: str | None = None
    best_overlap = 0
    for candidate in stored:
        overlap = len(incoming & set(candidate.member_unique_ids))
        if overlap > best_overlap or (
            overlap == best_overlap and best_id is not None and candidate.cell_id < best_id
        ):
            best_overlap = overlap
            best_id = candidate.cell_id
    return best_id
