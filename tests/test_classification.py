"""Cell classification tests."""

from __future__ import annotations

from custom_components.oikovis_pulse.classification import classify
from custom_components.oikovis_pulse.model import CellClass, SourceEntity


def _entity(entity_id: str, platform: str = "mqtt") -> SourceEntity:
    return SourceEntity(
        entity_id=entity_id,
        unique_id=entity_id,
        platform=platform,
        device_id="dev-1",
        device_class="battery",
        unit="%",
        state="50",
    )


def test_unknown_domain_defaults_to_replaceable() -> None:
    assert classify([_entity("sensor.a_battery", platform="some_new_integration")]) is (
        CellClass.REPLACEABLE
    )


def test_phone_domain_is_built_in() -> None:
    assert classify([_entity("sensor.phone_battery", platform="mobile_app")]) is CellClass.BUILT_IN


def test_vacuum_domain_is_built_in() -> None:
    assert classify([_entity("sensor.vac_battery", platform="roborock")]) is CellClass.BUILT_IN


def test_excluded_name_pattern_beats_domain_default() -> None:
    cell = [_entity("sensor.car_magic_soc", platform="cardata")]
    assert classify(cell) is CellClass.EXCLUDED


def test_user_override_beats_everything() -> None:
    cell = [_entity("sensor.phone_battery", platform="mobile_app")]
    assert classify(cell, override=CellClass.REPLACEABLE) is CellClass.REPLACEABLE


def test_empty_members_default_to_replaceable() -> None:
    assert classify([]) is CellClass.REPLACEABLE
