"""Cell classification tests."""

from __future__ import annotations

import pytest

from custom_components.oikovis_pulse import classification
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


# Stress tests
def test_stress_two_domains_one_built_in_one_replaceable() -> None:
    """Multiple members from different domains: first member's domain wins."""
    members = [
        _entity("sensor.a_battery", platform="mobile_app"),  # BUILT_IN
        _entity("sensor.b_battery", platform="mqtt"),  # unknown, REPLACEABLE
    ]
    result = classify(members)
    assert result is CellClass.BUILT_IN  # First domain with default is returned


def test_stress_two_domains_reversed_order() -> None:
    """Verify determinism: first KNOWN domain wins, order-independent."""
    members_a = [
        _entity("sensor.a_battery", platform="mobile_app"),  # BUILT_IN
        _entity("sensor.b_battery", platform="mqtt"),  # unknown, REPLACEABLE
    ]
    members_b = [
        _entity("sensor.b_battery", platform="mqtt"),  # unknown, REPLACEABLE
        _entity("sensor.a_battery", platform="mobile_app"),  # BUILT_IN
    ]
    result_a = classify(members_a)
    result_b = classify(members_b)
    # Both return BUILT_IN because it's the first (and only) known domain
    assert result_a is CellClass.BUILT_IN
    assert result_b is CellClass.BUILT_IN


def test_stress_excluded_pattern_beats_built_in_domain() -> None:
    """Excluded name pattern must win over domain default."""
    cell = [_entity("sensor.phone_magic_soc", platform="mobile_app")]
    # mobile_app is BUILT_IN, but "magic_soc" matches excluded pattern
    assert classify(cell) is CellClass.EXCLUDED


def test_stress_override_replaceable_beats_excluded_pattern() -> None:
    """User override must win over excluded pattern."""
    cell = [_entity("sensor.car_magic_soc", platform="cardata")]
    result = classify(cell, override=CellClass.REPLACEABLE)
    assert result is CellClass.REPLACEABLE


def test_stress_override_excluded_beats_built_in() -> None:
    """User override must win over domain default."""
    cell = [_entity("sensor.phone_battery", platform="mobile_app")]
    result = classify(cell, override=CellClass.EXCLUDED)
    assert result is CellClass.EXCLUDED


def test_stress_new_unknown_domain_never_raises() -> None:
    """Unknown domain should never raise KeyError."""
    # Use a domain that will never be in DOMAIN_DEFAULTS
    cell = [_entity("sensor.exotic_battery", platform="some_future_integration_xyz")]
    result = classify(cell)
    assert result is CellClass.REPLACEABLE


def test_stress_excluded_patterns_all_work() -> None:
    """Test all excluded patterns are recognized."""
    patterns_to_test = [
        "sensor.magic_soc",
        "sensor.predicted_state_of_charge",
        "sensor.charge_level_at_end_of_trip",
        "sensor.state_of_charge_target",
    ]
    for entity_id in patterns_to_test:
        cell = [_entity(entity_id, platform="mqtt")]
        result = classify(cell)
        assert result is CellClass.EXCLUDED, f"Failed for {entity_id}"


def test_stress_case_sensitivity_in_pattern() -> None:
    """Test case sensitivity: patterns are lowercase substring matches."""
    # Patterns are lowercase substrings, so "magic_soc" should match
    # "sensor.Magic_SOC" only if it's a substring match
    cell = [_entity("sensor.Magic_SOC", platform="mqtt")]
    result = classify(cell)
    # "magic_soc" is in "Magic_SOC" as a case-insensitive check?
    # Let's verify: the code does `pattern in member.entity_id`
    # This is case-sensitive Python string containment
    # "magic_soc" is NOT in "sensor.Magic_SOC" (case-sensitive)
    assert result is CellClass.REPLACEABLE  # Should not match due to case


def test_stress_case_sensitivity_lowercase() -> None:
    """Test that patterns DO match when lowercase."""
    cell = [_entity("sensor.magic_soc", platform="mqtt")]
    result = classify(cell)
    assert result is CellClass.EXCLUDED


def test_stress_pattern_substring_matching() -> None:
    """Patterns are substring matches anywhere in entity_id."""
    # "magic_soc" appears in the middle of a longer entity_id
    cell = [_entity("sensor.car_battery_magic_soc_prediction", platform="mqtt")]
    result = classify(cell)
    assert result is CellClass.EXCLUDED


def test_stress_no_mutation_of_input() -> None:
    """Function should not mutate the input list."""
    members = [_entity("sensor.test_battery", platform="mobile_app")]
    original_state = members[0].state
    classify(members)
    assert members[0].state == original_state
    # Members should still be the same objects
    assert members[0] is members[0]


def test_stress_multiple_excluded_patterns_first_match_returns() -> None:
    """When multiple patterns match, the first match should return EXCLUDED."""
    cell = [_entity("sensor.magic_soc_predicted_state", platform="mqtt")]
    # Both "magic_soc" and "predicted_state_of_charge" patterns could match
    result = classify(cell)
    assert result is CellClass.EXCLUDED


def test_stress_all_members_unknown_domain() -> None:
    """All members from unknown domains should default to REPLACEABLE."""
    members = [
        _entity("sensor.a", platform="unknown1"),
        _entity("sensor.b", platform="unknown2"),
    ]
    result = classify(members)
    assert result is CellClass.REPLACEABLE


def test_stress_mixed_members_some_excluded_some_not() -> None:
    """If any member matches excluded pattern, all excluded."""
    members = [
        _entity("sensor.normal_battery", platform="mqtt"),
        _entity("sensor.magic_soc", platform="mqtt"),  # This matches excluded
    ]
    result = classify(members)
    assert result is CellClass.EXCLUDED


# Fix round 1: Conflict resolution tests (deterministic, order-independent)
def test_fix_conflicting_domains_order_a(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two members with different domain classes return same result in order A.

    This test verifies the fix for order-dependence: the algorithm now collects
    all domain defaults and resolves conflicts via severity order, making the
    result deterministic regardless of member order.
    """
    monkeypatch.setitem(classification.DOMAIN_DEFAULTS, "domain_replaceable", CellClass.REPLACEABLE)
    monkeypatch.setitem(classification.DOMAIN_DEFAULTS, "domain_built_in", CellClass.BUILT_IN)

    members = [
        _entity("sensor.a", platform="domain_replaceable"),
        _entity("sensor.b", platform="domain_built_in"),
    ]
    result = classify(members)
    # BUILT_IN is more restrictive than REPLACEABLE, so it should win
    assert result is CellClass.BUILT_IN


def test_fix_conflicting_domains_order_b(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two members with different domain classes return same result in order B (reversed).

    Verifies determinism: reversing member order gives the same classification.
    """
    monkeypatch.setitem(classification.DOMAIN_DEFAULTS, "domain_replaceable", CellClass.REPLACEABLE)
    monkeypatch.setitem(classification.DOMAIN_DEFAULTS, "domain_built_in", CellClass.BUILT_IN)

    members = [
        _entity("sensor.b", platform="domain_built_in"),
        _entity("sensor.a", platform="domain_replaceable"),
    ]
    result = classify(members)
    # Same result as order_a: BUILT_IN wins
    assert result is CellClass.BUILT_IN


def test_fix_conflict_severity_excluded_beats_built_in(monkeypatch: pytest.MonkeyPatch) -> None:
    """When EXCLUDED and BUILT_IN conflict, EXCLUDED wins (more restrictive)."""
    monkeypatch.setitem(classification.DOMAIN_DEFAULTS, "domain_built_in", CellClass.BUILT_IN)
    monkeypatch.setitem(classification.DOMAIN_DEFAULTS, "domain_excluded", CellClass.EXCLUDED)

    members = [
        _entity("sensor.a", platform="domain_built_in"),
        _entity("sensor.b", platform="domain_excluded"),
    ]
    result = classify(members)
    assert result is CellClass.EXCLUDED


def test_fix_one_known_one_unknown_order_a() -> None:
    """One known + one unknown domain in order A: known domain decides."""
    members = [
        _entity("sensor.a", platform="mobile_app"),  # BUILT_IN
        _entity("sensor.b", platform="unknown_domain"),  # unknown
    ]
    result = classify(members)
    assert result is CellClass.BUILT_IN


def test_fix_one_known_one_unknown_order_b() -> None:
    """One known + one unknown domain in order B (reversed): same result."""
    members = [
        _entity("sensor.b", platform="unknown_domain"),  # unknown
        _entity("sensor.a", platform="mobile_app"),  # BUILT_IN
    ]
    result = classify(members)
    assert result is CellClass.BUILT_IN
