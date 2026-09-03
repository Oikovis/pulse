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
    """Classify a cell based on precedence rules.

    Precedence (left-to-right, final word):
    1. User override always wins.
    2. If ANY member matches an excluded-name pattern → EXCLUDED.
    3. If members are from domains in DOMAIN_DEFAULTS:
       - Collect all their classifications.
       - If they all agree → that class.
       - If they conflict → severity order wins: EXCLUDED > BUILT_IN > REPLACEABLE.
       - Rationale: telling someone to replace a battery that cannot be replaced
         is the worse error; the more restrictive classification wins.
    4. Otherwise → REPLACEABLE (safe default for unknown devices).

    Result is deterministic and does not depend on member order on any path.
    """
    if override is not None:
        return override

    for member in members:
        if any(pattern in member.entity_id for pattern in EXCLUDED_NAME_PATTERNS):
            return CellClass.EXCLUDED

    # Collect domain defaults from members whose platforms are known.
    domain_classes: set[CellClass] = set()
    for member in members:
        default = DOMAIN_DEFAULTS.get(member.platform)
        if default is not None:
            domain_classes.add(default)

    if not domain_classes:
        return CellClass.REPLACEABLE

    if len(domain_classes) == 1:
        return domain_classes.pop()

    # Conflict: multiple distinct classes. Resolve by severity: EXCLUDED > BUILT_IN > REPLACEABLE.
    if CellClass.EXCLUDED in domain_classes:
        return CellClass.EXCLUDED
    if CellClass.BUILT_IN in domain_classes:
        return CellClass.BUILT_IN
    return CellClass.REPLACEABLE
