"""Default classification of cells into replaceable, built-in and excluded."""

from __future__ import annotations

from collections.abc import Sequence

from .model import CellClass, SourceEntity

# A default, never a verdict. The map is always incomplete and every cell is
# user-overridable; it exists so a first run does not present a car's state of
# charge as a battery to replace.
DOMAIN_DEFAULTS: dict[str, CellClass] = {
    "mobile_app": CellClass.BUILT_IN,
    "icloud3": CellClass.BUILT_IN,
    "cardata": CellClass.BUILT_IN,
    "bmw_connected_drive": CellClass.BUILT_IN,
    "tesla_custom": CellClass.BUILT_IN,
    "nut": CellClass.BUILT_IN,
    "apcupsd": CellClass.BUILT_IN,
    "roborock": CellClass.BUILT_IN,
    "xiaomi_miio": CellClass.BUILT_IN,
    "sonos": CellClass.BUILT_IN,
}

EXCLUDED_NAME_PATTERNS: tuple[str, ...] = (
    "magic_soc",
    "predicted_state_of_charge",
    "charge_level_at_end_of_trip",
    "state_of_charge_target",
)


def classify(
    members: Sequence[SourceEntity],
    override: CellClass | None = None,
) -> CellClass:
    """Classify a cell. A user override always wins."""
    if override is not None:
        return override

    for member in members:
        if any(pattern in member.entity_id for pattern in EXCLUDED_NAME_PATTERNS):
            return CellClass.EXCLUDED

    for member in members:
        default = DOMAIN_DEFAULTS.get(member.platform)
        if default is not None:
            return default

    return CellClass.REPLACEABLE
