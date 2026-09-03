"""Data model for the Pulse battery fleet."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ReadingKind(StrEnum):
    """How a cell reports its level."""

    PERCENTAGE = "percentage"
    BINARY = "binary"
    NONE = "none"


class CellClass(StrEnum):
    """What kind of battery a cell is."""

    REPLACEABLE = "replaceable"
    BUILT_IN = "built_in"
    EXCLUDED = "excluded"


@dataclass(frozen=True)
class SourceEntity:
    """A Home Assistant entity that reports something about a battery."""

    entity_id: str
    unique_id: str
    platform: str
    device_id: str | None
    device_class: str | None
    unit: str | None
    state: str
    disabled: bool = False
    hidden: bool = False


@dataclass(frozen=True)
class BatteryNote:
    """Metadata published by the Battery Notes integration."""

    source_entity_id: str | None
    device_id: str | None
    battery_type: str | None = None
    battery_quantity: int | None = None
    low_threshold: float | None = None
    last_replaced: str | None = None


@dataclass
class CellMetadata:
    """Resolved metadata for one cell."""

    battery_type: str | None = None
    battery_quantity: int | None = None
    last_replaced: str | None = None
    low_threshold: float | None = None
    bn_low_threshold: float | None = None


@dataclass
class Cell:
    """One physical battery."""

    cell_id: str
    members: tuple[str, ...]
    reading_kind: ReadingKind = ReadingKind.NONE
    percentage: float | None = None
    low: bool = False
    critical: bool = False
    charging: bool = False
    cell_class: CellClass = CellClass.REPLACEABLE
    metadata: CellMetadata = field(default_factory=CellMetadata)
    gone_since: str | None = None


@dataclass
class Unit:
    """A device, or a synthetic device standing in for an orphan entity."""

    unit_id: str
    name: str
    area_id: str | None
    cells: list[Cell] = field(default_factory=list)
    unresolved_note: bool = False
    # Unused in v1. A bridged second instance is already a real situation, so
    # the field exists now to keep multi-site from becoming a migration later.
    instance: str | None = None
    duplicate_of: str | None = None
    link_candidate: str | None = None
