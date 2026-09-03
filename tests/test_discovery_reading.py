"""Reading resolution tests."""

from __future__ import annotations

from custom_components.oikovis_pulse.discovery import resolve_reading
from custom_components.oikovis_pulse.model import ReadingKind, SourceEntity


def _entity(entity_id: str, unit: str | None, state: str) -> SourceEntity:
    return SourceEntity(
        entity_id=entity_id,
        unique_id=entity_id,
        platform="mqtt",
        device_id="dev-1",
        device_class="battery",
        unit=unit,
        state=state,
    )


def test_percentage_wins_when_usable() -> None:
    kind, pct, low, critical = resolve_reading(
        [
            _entity("sensor.a_battery", "%", "87"),
            _entity("binary_sensor.a_battery_low", None, "off"),
        ]
    )
    assert kind is ReadingKind.PERCENTAGE
    assert pct == 87.0
    assert low is False
    assert critical is False


def test_dead_percentage_falls_back_to_binary() -> None:
    """The live bug this rule exists to prevent."""
    kind, pct, low, _ = resolve_reading(
        [
            _entity("sensor.a_battery", "%", "unavailable"),
            _entity("binary_sensor.a_battery_low", None, "on"),
        ]
    )
    assert kind is ReadingKind.BINARY
    assert pct is None
    assert low is True


def test_all_dead_reads_none() -> None:
    kind, pct, low, critical = resolve_reading(
        [
            _entity("sensor.a_battery", "%", "unavailable"),
            _entity("binary_sensor.a_battery_low", None, "unknown"),
        ]
    )
    assert kind is ReadingKind.NONE
    assert pct is None
    assert low is False
    assert critical is False


def test_critical_flag_is_reported_alongside_percentage() -> None:
    """Flag wins for alerting, number wins for display."""
    kind, pct, _, critical = resolve_reading(
        [
            _entity("sensor.a_battery", "%", "80"),
            _entity("binary_sensor.a_battery_critical", None, "on"),
        ]
    )
    assert kind is ReadingKind.PERCENTAGE
    assert pct == 80.0
    assert critical is True


def test_non_numeric_percentage_is_not_usable() -> None:
    kind, pct, _, _ = resolve_reading([_entity("sensor.a_battery", "%", "not_a_number")])
    assert kind is ReadingKind.NONE
    assert pct is None


def test_no_members_reads_none() -> None:
    assert resolve_reading([])[0] is ReadingKind.NONE


# Stress tests below


def test_stress_empty_string_percentage_not_a_number() -> None:
    """Empty string state should not be treated as a reading."""
    kind, pct, low, critical = resolve_reading([_entity("sensor.a_battery", "%", "")])
    assert kind is ReadingKind.NONE
    assert pct is None
    assert low is False
    assert critical is False


def test_stress_invalid_number_format() -> None:
    """Non-numeric percentage (12,5 with comma) should not be treated as a reading."""
    kind, pct, low, critical = resolve_reading([_entity("sensor.a_battery", "%", "12,5")])
    assert kind is ReadingKind.NONE
    assert pct is None
    assert low is False
    assert critical is False


def test_stress_unavailable_percentage_with_on_flag() -> None:
    """Percentage at unavailable should not prevent binary flag from being read."""
    kind, pct, low, critical = resolve_reading(
        [
            _entity("sensor.a_battery", "%", "unavailable"),
            _entity("binary_sensor.a_battery_low", None, "on"),
        ]
    )
    assert kind is ReadingKind.BINARY
    assert pct is None
    assert low is True
    assert critical is False


def test_stress_case_insensitive_on_state() -> None:
    """ON/on/On should all be recognized as truthy flag state."""
    # Test uppercase ON
    kind, pct, low, _ = resolve_reading([_entity("binary_sensor.a_battery_low", None, "ON")])
    assert kind is ReadingKind.BINARY
    assert low is True

    # Test uppercase OFF
    kind2, pct2, low2, _ = resolve_reading([_entity("binary_sensor.a_battery_low", None, "OFF")])
    assert kind2 is ReadingKind.BINARY
    assert low2 is False


def test_stress_whitespace_around_on_state() -> None:
    """Whitespace around on/off should be trimmed and recognized."""
    kind, pct, low, _ = resolve_reading([_entity("binary_sensor.a_battery_low", None, " on ")])
    assert kind is ReadingKind.BINARY
    assert low is True


def test_stress_case_insensitive_unavailable() -> None:
    """Case variations of unavailable should all be treated as unusable."""
    # Capitalized Unavailable
    kind, pct, _, _ = resolve_reading([_entity("sensor.a_battery", "%", "Unavailable")])
    assert kind is ReadingKind.NONE
    assert pct is None

    # All uppercase UNAVAILABLE
    kind2, pct2, _, _ = resolve_reading([_entity("sensor.a_battery", "%", "UNAVAILABLE")])
    assert kind2 is ReadingKind.NONE
    assert pct2 is None


def test_stress_two_usable_percentages_first_wins() -> None:
    """When two percentage members are usable, the first one should win."""
    kind, pct, low, critical = resolve_reading(
        [
            _entity("sensor.a_battery", "%", "75"),
            _entity("sensor.a_battery_level", "%", "85"),
        ]
    )
    assert kind is ReadingKind.PERCENTAGE
    assert pct == 75.0  # First one should win
    assert low is False
    assert critical is False


def test_stress_negative_percentage() -> None:
    """Negative percentage should still be accepted as float, no clamping."""
    kind, pct, low, critical = resolve_reading([_entity("sensor.a_battery", "%", "-5")])
    assert kind is ReadingKind.PERCENTAGE
    assert pct == -5.0  # No clamping, negative is accepted
    assert low is False
    assert critical is False


def test_stress_over_100_percentage() -> None:
    """Percentage over 100 should still be accepted as float, no clamping."""
    kind, pct, low, critical = resolve_reading([_entity("sensor.a_battery", "%", "150")])
    assert kind is ReadingKind.PERCENTAGE
    assert pct == 150.0  # No clamping, over 100 is accepted
    assert low is False
    assert critical is False


def test_stress_float_percentage() -> None:
    """Float percentages should be accepted."""
    kind, pct, low, critical = resolve_reading([_entity("sensor.a_battery", "%", "87.5")])
    assert kind is ReadingKind.PERCENTAGE
    assert pct == 87.5
    assert low is False
    assert critical is False


def test_stress_off_flag_not_triggering_low() -> None:
    """Off state should not set low flag."""
    kind, pct, low, _ = resolve_reading([_entity("binary_sensor.a_battery_low", None, "off")])
    assert kind is ReadingKind.BINARY
    assert low is False


def test_stress_multiple_flags_low_and_critical() -> None:
    """Both low and critical flags on should both be captured."""
    kind, pct, low, critical = resolve_reading(
        [
            _entity("binary_sensor.a_battery_low", None, "on"),
            _entity("binary_sensor.a_battery_critical", None, "on"),
        ]
    )
    assert kind is ReadingKind.BINARY
    assert pct is None
    assert low is True
    assert critical is True


def test_stress_critical_flag_with_off_state() -> None:
    """Critical flag off should not be treated as truthy."""
    kind, pct, low, critical = resolve_reading(
        [_entity("binary_sensor.a_battery_critical", None, "off")]
    )
    assert kind is ReadingKind.BINARY
    assert pct is None
    assert low is False
    assert critical is False


def test_stress_unknown_state_binary_flag() -> None:
    """Unknown state on a binary sensor should be treated as unusable."""
    kind, pct, low, critical = resolve_reading(
        [_entity("binary_sensor.a_battery_low", None, "unknown")]
    )
    assert kind is ReadingKind.NONE
    assert pct is None
    assert low is False
    assert critical is False


def test_stress_none_state_binary_flag() -> None:
    """None state should be treated as unusable."""
    kind, pct, low, critical = resolve_reading([_entity("binary_sensor.a_battery_low", None, "none")])
    assert kind is ReadingKind.NONE
    assert pct is None
    assert low is False
    assert critical is False
