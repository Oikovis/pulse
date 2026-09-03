"""Adapter conversion tests, using stubs rather than a live hass."""

from __future__ import annotations

from dataclasses import dataclass

from custom_components.oikovis_pulse.adapter import entity_to_dto


@dataclass
class _RegEntry:
    entity_id: str
    unique_id: str
    platform: str
    device_id: str | None = "dev-1"
    disabled_by: str | None = None
    hidden_by: str | None = None


@dataclass
class _State:
    state: str
    attributes: dict[str, object]


def test_converts_a_battery_sensor() -> None:
    entry = _RegEntry("sensor.a_battery", "uid-a", "mqtt")
    state = _State("77", {"device_class": "battery", "unit_of_measurement": "%"})
    dto = entity_to_dto(entry, state)
    assert dto is not None
    assert dto.unique_id == "uid-a"
    assert dto.platform == "mqtt"
    assert dto.unit == "%"
    assert dto.state == "77"


def test_missing_state_yields_none() -> None:
    entry = _RegEntry("sensor.a_battery", "uid-a", "mqtt")
    assert entity_to_dto(entry, None) is None


def test_disabled_and_hidden_flags_are_carried() -> None:
    entry = _RegEntry("sensor.a_battery", "uid-a", "mqtt", disabled_by="user", hidden_by="user")
    state = _State("77", {"device_class": "battery", "unit_of_measurement": "%"})
    dto = entity_to_dto(entry, state)
    assert dto is not None
    assert dto.disabled is True
    assert dto.hidden is True


def test_entity_without_unique_id_is_skipped() -> None:
    """Identity depends on unique_id; an entity without one cannot be tracked."""
    entry = _RegEntry("sensor.a_battery", "", "mqtt")
    state = _State("77", {"device_class": "battery", "unit_of_measurement": "%"})
    assert entity_to_dto(entry, state) is None
