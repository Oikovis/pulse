"""Candidate filtering tests."""

from __future__ import annotations

from custom_components.oikovis_pulse.discovery import filter_candidates
from custom_components.oikovis_pulse.model import SourceEntity


def _entity(entity_id: str, **kwargs: object) -> SourceEntity:
    defaults: dict[str, object] = {
        "unique_id": entity_id,
        "platform": "mqtt",
        "device_id": "dev-1",
        "device_class": "battery",
        "unit": "%",
        "state": "50",
        "disabled": False,
        "hidden": False,
    }
    defaults.update(kwargs)
    return SourceEntity(entity_id=entity_id, **defaults)  # type: ignore[arg-type]


def test_keeps_plain_battery_entity() -> None:
    kept = filter_candidates([_entity("sensor.hall_battery")])
    assert [e.entity_id for e in kept] == ["sensor.hall_battery"]


def test_drops_battery_notes_mirrors_by_platform() -> None:
    entities = [
        _entity("sensor.hall_battery"),
        _entity("sensor.hall_battery_plus", platform="battery_notes"),
    ]
    kept = filter_candidates(entities)
    assert [e.entity_id for e in kept] == ["sensor.hall_battery"]


def test_drops_disabled_and_hidden() -> None:
    entities = [
        _entity("sensor.a_battery", disabled=True),
        _entity("sensor.b_battery", hidden=True),
        _entity("sensor.c_battery"),
    ]
    kept = filter_candidates(entities)
    assert [e.entity_id for e in kept] == ["sensor.c_battery"]


def test_drops_non_battery_device_class() -> None:
    entities = [
        _entity("sensor.hall_temperature", device_class="temperature"),
        _entity("sensor.hall_battery"),
    ]
    kept = filter_candidates(entities)
    assert [e.entity_id for e in kept] == ["sensor.hall_battery"]


def test_mirror_named_like_a_source_is_still_dropped() -> None:
    """Name says 'critical', platform says battery_notes. Platform wins."""
    entities = [
        _entity("binary_sensor.lock_keypad_battery_critical", unit=None, state="off"),
        _entity(
            "binary_sensor.lock_keypad_battery_critical_battery_plus_low",
            platform="battery_notes",
            unit=None,
            state="off",
        ),
    ]
    kept = filter_candidates(entities)
    assert [e.entity_id for e in kept] == ["binary_sensor.lock_keypad_battery_critical"]
