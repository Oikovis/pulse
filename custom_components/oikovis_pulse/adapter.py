"""Convert Home Assistant registry and state objects into plain DTOs.

Everything above this module reasons about DTOs only, so the reasoning is
testable without a running Home Assistant.
"""

from __future__ import annotations

from typing import Any

from .model import SourceEntity


def entity_to_dto(registry_entry: Any, state: Any) -> SourceEntity | None:
    """Build a SourceEntity, or None when the entity cannot be tracked."""
    if state is None:
        return None
    if not getattr(registry_entry, "unique_id", None):
        return None

    attributes = getattr(state, "attributes", {}) or {}
    return SourceEntity(
        entity_id=registry_entry.entity_id,
        unique_id=registry_entry.unique_id,
        platform=registry_entry.platform,
        device_id=getattr(registry_entry, "device_id", None),
        device_class=attributes.get("device_class"),
        unit=attributes.get("unit_of_measurement"),
        state=str(getattr(state, "state", "")),
        disabled=getattr(registry_entry, "disabled_by", None) is not None,
        hidden=getattr(registry_entry, "hidden_by", None) is not None,
    )
