"""Stress test edge cases for cell grouping."""

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


def test_stress_entity_id_is_only_suffix() -> None:
    """Entity whose object_id is purely a suffix (e.g. sensor.battery)."""
    # Even if object_id is only "battery", name_stem should handle it
    stem = name_stem("sensor.battery")
    assert stem != "", "stem should not be empty string"
    # After removing _battery, we get empty string, then numeric strip returns empty,
    # so stem becomes ""
    # But this shouldn't crash and should not merge unrelated entities

    entities = [
        _entity("sensor.battery", unit="%", state="50"),
        _entity("sensor.lock_battery", unit="%", state="75"),
    ]
    cells = group_into_cells(entities)
    assert len(cells) == 2, f"Expected 2 cells for distinct battery entities, got {len(cells)}"


def test_stress_numeric_and_battery_suffix_composition() -> None:
    """Name carrying both numeric suffix and battery suffix."""
    stem = name_stem("sensor.lock_battery_2")
    assert stem == "lock", f"Expected 'lock', got '{stem}'"

    stem = name_stem("binary_sensor.door_sensor_battery_low_3")
    assert stem == "door_sensor", f"Expected 'door_sensor', got '{stem}'"


def test_stress_note_for_nonexistent_entity() -> None:
    """BatteryNote whose source_entity_id is NOT in the input list."""
    entities = [
        _entity("sensor.lock_battery", unit="%", state="50"),
    ]
    notes = [BatteryNote(source_entity_id="sensor.missing_battery", device_id="dev-1")]

    # Should not raise and should not create phantom cell
    cells = group_into_cells(entities, notes)
    assert len(cells) == 1, f"Expected 1 cell, got {len(cells)}"
    assert cells[0][0].entity_id == "sensor.lock_battery"


def test_stress_no_entity_drops_or_duplicates() -> None:
    """Every input entity appears in exactly one output cell."""
    entities = [
        _entity("sensor.door_battery", unit="%", state="100"),
        _entity("binary_sensor.door_battery_low"),
        _entity("sensor.lock_battery", unit="%", state="50"),
        _entity("binary_sensor.lock_keypad_battery_critical"),
    ]
    notes = [BatteryNote(source_entity_id="sensor.lock_battery", device_id="dev-1")]

    cells = group_into_cells(entities, notes)

    # Flatten all cells
    all_entity_ids = []
    for cell in cells:
        for entity in cell:
            all_entity_ids.append(entity.entity_id)

    # Verify coverage: all input entities present exactly once
    input_ids = {e.entity_id for e in entities}
    output_ids = set(all_entity_ids)
    assert input_ids == output_ids, f"Mismatch: input={input_ids}, output={output_ids}"
    assert len(all_entity_ids) == len(output_ids), (
        f"Duplicate in output: {len(all_entity_ids)} items " f"but {len(output_ids)} unique"
    )


def test_stress_noted_entity_not_in_stem_group() -> None:
    """Noted entity must not also appear in stem-based grouping."""
    entities = [
        _entity("sensor.lock_battery", unit="%", state="18"),
        _entity("sensor.lock_battery_secondary", unit="%", state="90"),
    ]
    notes = [BatteryNote(source_entity_id="sensor.lock_battery_secondary", device_id="dev-1")]

    cells = group_into_cells(entities, notes)

    # Find the secondary cell
    secondary_cell = None
    for cell in cells:
        entity_ids = {e.entity_id for e in cell}
        if "sensor.lock_battery_secondary" in entity_ids:
            secondary_cell = cell
            break

    assert secondary_cell is not None, "Secondary entity missing"
    assert len(secondary_cell) == 1, (
        f"Secondary should be alone, but cell has: " f"{[e.entity_id for e in secondary_cell]}"
    )
    assert secondary_cell[0].entity_id == "sensor.lock_battery_secondary"


def test_stress_empty_input_multiple_ways() -> None:
    """Empty input, empty notes, various combinations."""
    assert group_into_cells([]) == []
    assert group_into_cells([], []) == []
    assert (
        group_into_cells(
            [],
            [BatteryNote(source_entity_id="sensor.missing", device_id="dev-1")],
        )
        == []
    )
