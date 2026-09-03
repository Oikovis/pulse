"""Battery Notes parsing and primary cell resolution."""

from __future__ import annotations

from custom_components.oikovis_pulse.battery_notes import parse_note, pick_primary_cell
from custom_components.oikovis_pulse.model import Cell, SourceEntity


def _entity(entity_id: str, unit: str | None = "%", state: str = "50") -> SourceEntity:
    return SourceEntity(
        entity_id=entity_id,
        unique_id=entity_id,
        platform="mqtt",
        device_id="dev-1",
        device_class="battery",
        unit=unit,
        state=state,
    )


def test_parse_device_level_note_has_no_source_entity() -> None:
    note = parse_note(
        {
            "battery_type": "Rechargeable",
            "battery_quantity": 1,
            "battery_low_threshold": 15.0,
            "battery_last_replaced": None,
            "source_entity_id": "",
        },
        device_id="dev-1",
    )
    assert note.source_entity_id is None
    assert note.device_id == "dev-1"
    assert note.battery_type == "Rechargeable"
    assert note.low_threshold == 15.0


def test_parse_entity_level_note_keeps_source_entity() -> None:
    note = parse_note(
        {
            "battery_type": "AA",
            "battery_quantity": 2,
            "source_entity_id": "binary_sensor.lock_keypad_battery_critical",
        },
        device_id="dev-1",
    )
    assert note.source_entity_id == "binary_sensor.lock_keypad_battery_critical"
    assert note.battery_quantity == 2


def test_primary_is_the_only_percentage_cell() -> None:
    cells = [Cell("c1", ("sensor.lock_battery",)), Cell("c2", ("binary_sensor.lock_keypad",))]
    members = {
        "c1": [_entity("sensor.lock_battery")],
        "c2": [_entity("binary_sensor.lock_keypad", unit=None, state="off")],
    }
    assert pick_primary_cell(cells, members, "Lock") == "c1"


def test_primary_prefers_the_stem_closest_to_the_device_name() -> None:
    cells = [Cell("c1", ("sensor.phone_battery",)), Cell("c2", ("sensor.phone_watch_battery",))]
    members = {
        "c1": [_entity("sensor.phone_battery")],
        "c2": [_entity("sensor.phone_watch_battery")],
    }
    assert pick_primary_cell(cells, members, "Phone") == "c1"


def test_primary_refuses_to_guess_when_ambiguous() -> None:
    """Two equally distant percentage cells: attach the note to neither."""
    cells = [Cell("c1", ("sensor.alpha_battery",)), Cell("c2", ("sensor.beta_battery",))]
    members = {
        "c1": [_entity("sensor.alpha_battery")],
        "c2": [_entity("sensor.beta_battery")],
    }
    assert pick_primary_cell(cells, members, "Gamma") is None


def test_no_percentage_cells_means_no_primary() -> None:
    cells = [Cell("c1", ("binary_sensor.a_battery_low",))]
    members = {"c1": [_entity("binary_sensor.a_battery_low", unit=None, state="off")]}
    assert pick_primary_cell(cells, members, "A") is None


# Stress tests for parse_note
def test_parse_note_all_empty_attributes() -> None:
    """Empty attributes must not raise."""
    note = parse_note({}, device_id=None)
    assert note.source_entity_id is None
    assert note.device_id is None
    assert note.battery_type is None
    assert note.battery_quantity is None
    assert note.low_threshold is None
    assert note.last_replaced is None


def test_parse_note_quantity_as_string() -> None:
    """battery_quantity may arrive as a string."""
    note = parse_note({"battery_quantity": "2"}, device_id=None)
    assert note.battery_quantity == 2


def test_parse_note_quantity_as_int() -> None:
    """battery_quantity may arrive as an int."""
    note = parse_note({"battery_quantity": 1}, device_id=None)
    assert note.battery_quantity == 1


def test_parse_note_quantity_as_none() -> None:
    """battery_quantity may be None."""
    note = parse_note({"battery_quantity": None}, device_id=None)
    assert note.battery_quantity is None


def test_parse_note_quantity_as_garbage() -> None:
    """battery_quantity as garbage must not raise; must produce None."""
    note = parse_note({"battery_quantity": "many"}, device_id=None)
    assert note.battery_quantity is None


def test_parse_note_threshold_as_string() -> None:
    """battery_low_threshold may arrive as a string."""
    note = parse_note({"battery_low_threshold": "15.0"}, device_id=None)
    assert note.low_threshold == 15.0


def test_parse_note_threshold_as_garbage() -> None:
    """battery_low_threshold as garbage must not raise; must produce None."""
    note = parse_note({"battery_low_threshold": "not_a_number"}, device_id=None)
    assert note.low_threshold is None


def test_parse_note_device_id_from_attributes_overrides_parameter() -> None:
    """device_id in attributes takes precedence."""
    note = parse_note({"device_id": "dev-2"}, device_id="dev-1")
    assert note.device_id == "dev-2"


def test_parse_note_empty_source_entity_id_becomes_none() -> None:
    """Empty string source_entity_id converts to None (device-level note)."""
    note = parse_note({"source_entity_id": ""}, device_id=None)
    assert note.source_entity_id is None


# Stress tests for pick_primary_cell
def test_pick_primary_cell_zero_cells() -> None:
    """Zero cells means no primary."""
    result = pick_primary_cell([], {}, "Device")
    assert result is None


def test_pick_primary_cell_one_cell_with_no_percentage_member() -> None:
    """One cell with no percentage member means no primary."""
    cells = [Cell("c1", ("binary_sensor.a_battery_low",))]
    members = {"c1": [_entity("binary_sensor.a_battery_low", unit=None, state="off")]}
    result = pick_primary_cell(cells, members, "A")
    assert result is None


def test_pick_primary_cell_two_percentage_cells_neither_matches_device_name() -> None:
    """Two percentage cells, neither stem matches device name, must return None."""
    cells = [Cell("c1", ("sensor.alpha_battery",)), Cell("c2", ("sensor.beta_battery",))]
    members = {
        "c1": [_entity("sensor.alpha_battery")],
        "c2": [_entity("sensor.beta_battery")],
    }
    result = pick_primary_cell(cells, members, "Gamma")
    assert result is None


def test_pick_primary_cell_two_percentage_cells_one_matches_device_name() -> None:
    """Two percentage cells, exactly one stem matches device name, return that one."""
    cells = [Cell("c1", ("sensor.foo_battery",)), Cell("c2", ("sensor.alpha_battery",))]
    members = {
        "c1": [_entity("sensor.foo_battery")],
        "c2": [_entity("sensor.alpha_battery")],
    }
    result = pick_primary_cell(cells, members, "Alpha")
    assert result == "c2"


def test_pick_primary_cell_device_name_with_punctuation_and_mixed_case() -> None:
    """Device name with punctuation and mixed case should normalise correctly."""
    cells = [Cell("c1", ("sensor.hall_sensor_battery",))]
    members = {"c1": [_entity("sensor.hall_sensor_battery")]}
    result = pick_primary_cell(cells, members, "Hall Sensor - Main")
    assert result == "c1"


def test_pick_primary_cell_proves_no_positional_fallback() -> None:
    """Prove pick_primary_cell does NOT return first cell purely on position.

    This test would fail if the code fell back to returning percentage_cells[0]
    when ambiguous. By putting the intended answer in position 2, we verify
    the function returns None for ambiguity rather than picking position 0.
    """
    cells = [
        Cell("c_first", ("sensor.first_battery",)),
        Cell("c_second", ("sensor.second_battery",)),
    ]
    members = {
        "c_first": [_entity("sensor.first_battery")],
        "c_second": [_entity("sensor.second_battery")],
    }
    # Device name matches neither "first" nor "second", so must return None,
    # NOT "c_first" just because it's first in the list.
    result = pick_primary_cell(cells, members, "Unrelated")
    assert result is None


def test_pick_primary_cell_no_members_mapping_for_cell_id() -> None:
    """If members_by_cell lacks a cell_id, that cell has no percentage member."""
    cells = [Cell("c1", ("sensor.test_battery",))]
    members: dict[str, list[SourceEntity]] = {}  # Empty, no members for c1
    result = pick_primary_cell(cells, members, "Test")
    assert result is None
