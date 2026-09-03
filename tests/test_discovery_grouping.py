"""Cell grouping tests."""

from __future__ import annotations

from custom_components.oikovis_pulse.discovery import group_into_cells, name_stem
from custom_components.oikovis_pulse.model import BatteryNote, SourceEntity


def _entity(entity_id: str, unit: str | None = None, state: str = "off") -> SourceEntity:
    return SourceEntity(
        entity_id=entity_id,
        unique_id=entity_id,
        platform="mqtt",
        device_id="dev-1",
        device_class="battery",
        unit=unit,
        state=state,
    )


def test_name_stem_strips_battery_suffixes() -> None:
    assert name_stem("sensor.hall_sensor_battery") == "hall_sensor"
    assert name_stem("binary_sensor.hall_sensor_battery_low") == "hall_sensor"
    assert name_stem("binary_sensor.hall_sensor_battery_critical") == "hall_sensor"
    assert name_stem("sensor.hall_sensor_battery_level") == "hall_sensor"
    assert name_stem("binary_sensor.hall_sensor_low_battery") == "hall_sensor"
    assert name_stem("binary_sensor.hall_sensor_batt") == "hall_sensor"


def test_name_stem_strips_numeric_duplicate_suffix() -> None:
    assert name_stem("binary_sensor.hall_sensor_battery_low_2") == "hall_sensor"


def test_percentage_and_flag_for_one_cell_group_together() -> None:
    cells = group_into_cells(
        [
            _entity("sensor.leak_sensor_battery", unit="%", state="100"),
            _entity("binary_sensor.leak_sensor_battery_low"),
        ]
    )
    assert len(cells) == 1
    assert len(cells[0]) == 2


def test_distinct_cells_on_one_device_stay_separate() -> None:
    cells = group_into_cells(
        [
            _entity("sensor.lock_battery", unit="%", state="18"),
            _entity("binary_sensor.lock_keypad_battery_critical"),
            _entity("binary_sensor.lock_door_sensor_battery_critical"),
        ]
    )
    assert len(cells) == 3


def test_entity_level_note_forces_its_own_cell() -> None:
    """An explicit note beats the name-stem heuristic."""
    entities = [
        _entity("sensor.lock_battery", unit="%", state="18"),
        _entity("sensor.lock_battery_secondary", unit="%", state="90"),
    ]
    notes = [BatteryNote(source_entity_id="sensor.lock_battery_secondary", device_id="dev-1")]
    cells = group_into_cells(entities, notes)
    assert len(cells) == 2
    assert any([e.entity_id for e in cell] == ["sensor.lock_battery_secondary"] for cell in cells)


def test_empty_input_produces_no_cells() -> None:
    assert group_into_cells([]) == []


def test_device_name_numeric_suffix_not_stripped() -> None:
    """Device name with trailing digit is distinct from same name without digit."""
    assert name_stem("sensor.lock_2_battery") == "lock_2"
    assert name_stem("sensor.lock_battery") == "lock"
    assert name_stem("sensor.lock_2_battery") != name_stem("sensor.lock_battery")


def test_multiple_batteries_with_numeric_device_names() -> None:
    """Two batteries on one device with numeric device names must not merge."""
    cells = group_into_cells(
        [
            _entity("sensor.lock_2_battery", unit="%", state="50"),
            _entity("sensor.lock_battery", unit="%", state="75"),
        ]
    )
    assert len(cells) == 2, f"Expected 2 separate cells for lock_2 and lock, got {len(cells)}"
