"""Suspicion flagging: duplicates across integrations, split units."""

from __future__ import annotations

from custom_components.oikovis_pulse.model import Cell, CellMetadata, ReadingKind, Unit
from custom_components.oikovis_pulse.suspicions import flag_suspicions


def _cell(
    cell_id: str,
    kind: ReadingKind,
    pct: float | None = None,
    btype: str | None = None,
) -> Cell:
    return Cell(
        cell_id=cell_id,
        members=(f"uid-{cell_id}",),
        reading_kind=kind,
        percentage=pct,
        metadata=CellMetadata(battery_type=btype),
    )


def test_near_identical_names_and_readings_flag_as_duplicates() -> None:
    units = [
        Unit("d1", "Leak Sensor", None, [_cell("c1", ReadingKind.PERCENTAGE, 100.0, "CR2032")]),
        Unit(
            "d2",
            "Select Leak Sensor",
            None,
            [_cell("c2", ReadingKind.PERCENTAGE, 100.0, "CR2032")],
        ),
    ]
    flag_suspicions(units)
    assert units[1].duplicate_of == "d1" or units[0].duplicate_of == "d2"


def test_different_devices_are_not_flagged() -> None:
    units = [
        Unit("d1", "Hall Sensor", None, [_cell("c1", ReadingKind.PERCENTAGE, 100.0, "CR2032")]),
        Unit("d2", "Garden Gate", None, [_cell("c2", ReadingKind.PERCENTAGE, 12.0, "AA")]),
    ]
    flag_suspicions(units)
    assert units[0].duplicate_of is None
    assert units[1].duplicate_of is None


def test_dead_unit_plus_orphan_flags_a_link_candidate() -> None:
    """Metadata on the device, the number on an orphan."""
    units = [
        Unit("d1", "Radiator Valve", None, [_cell("c1", ReadingKind.NONE, None, "3x AAA")]),
        Unit(
            "orphan:sensor.radiator_valve_battery",
            "radiator_valve_battery",
            None,
            [_cell("c2", ReadingKind.PERCENTAGE, 100.0)],
        ),
    ]
    flag_suspicions(units)
    assert units[0].link_candidate == "orphan:sensor.radiator_valve_battery"


def test_healthy_unit_gets_no_link_candidate() -> None:
    units = [
        Unit("d1", "Radiator Valve", None, [_cell("c1", ReadingKind.PERCENTAGE, 80.0)]),
        Unit(
            "orphan:sensor.radiator_valve_battery",
            "radiator_valve_battery",
            None,
            [_cell("c2", ReadingKind.PERCENTAGE, 100.0)],
        ),
    ]
    flag_suspicions(units)
    assert units[0].link_candidate is None


def test_flagging_never_mutates_cells() -> None:
    unit = Unit("d1", "Hall Sensor", None, [_cell("c1", ReadingKind.PERCENTAGE, 50.0)])
    flag_suspicions([unit])
    assert unit.cells[0].percentage == 50.0


def test_duplicate_flagging_is_deterministic_order_a() -> None:
    """Duplicates flagged in forward order: smaller unit_id is always reference."""
    units = [
        Unit("d1", "Sensor", None, [_cell("c1", ReadingKind.PERCENTAGE, 100.0, "CR2032")]),
        Unit("d2", "Sensor", None, [_cell("c2", ReadingKind.PERCENTAGE, 100.0, "CR2032")]),
    ]
    flag_suspicions(units)
    # d1 < d2, so d1 is reference, d2 points to d1.
    assert units[0].duplicate_of is None
    assert units[1].duplicate_of == "d1"


def test_duplicate_flagging_is_deterministic_order_b() -> None:
    """Duplicates flagged in reversed order: smaller unit_id is always reference."""
    units = [
        Unit("d2", "Sensor", None, [_cell("c2", ReadingKind.PERCENTAGE, 100.0, "CR2032")]),
        Unit("d1", "Sensor", None, [_cell("c1", ReadingKind.PERCENTAGE, 100.0, "CR2032")]),
    ]
    flag_suspicions(units)
    # d1 < d2, so d1 is reference (even though d1 appears second).
    # units[0] is d2, units[1] is d1.
    assert units[1].duplicate_of is None
    assert units[0].duplicate_of == "d1"


def test_three_way_duplicates_all_point_to_smallest() -> None:
    """Three or more units with same shape: all point to smallest unit_id, never chain."""
    units = [
        Unit("d1", "Sensor", None, [_cell("c1", ReadingKind.PERCENTAGE, 100.0, "CR2032")]),
        Unit("d2", "Sensor", None, [_cell("c2", ReadingKind.PERCENTAGE, 100.0, "CR2032")]),
        Unit("d3", "Sensor", None, [_cell("c3", ReadingKind.PERCENTAGE, 100.0, "CR2032")]),
    ]
    flag_suspicions(units)
    # d1 is smallest, so d2 and d3 both point to d1 (not d2->d1, d3->d2).
    assert units[0].duplicate_of is None
    assert units[1].duplicate_of == "d1"
    assert units[2].duplicate_of == "d1"


def test_cells_in_different_order_still_match() -> None:
    """Two units with same cells but different order are still flagged as duplicates."""
    units = [
        Unit(
            "d1",
            "Multi Cell Device",
            None,
            [
                _cell("c1a", ReadingKind.PERCENTAGE, 50.0, "AA"),
                _cell("c1b", ReadingKind.PERCENTAGE, 80.0, "CR2032"),
            ],
        ),
        Unit(
            "d2",
            "Multi Cell Device",
            None,
            [
                _cell("c2a", ReadingKind.PERCENTAGE, 80.0, "CR2032"),
                _cell("c2b", ReadingKind.PERCENTAGE, 50.0, "AA"),
            ],
        ),
    ]
    flag_suspicions(units)
    # Same cells in different order should still match.
    assert units[1].duplicate_of == "d1"


def test_link_candidate_requires_exact_name_match() -> None:
    """Orphan link candidates must match via exact name equality, not substring."""
    units = [
        Unit("d1", "Hall", None, [_cell("c1", ReadingKind.NONE)]),
        Unit(
            "orphan:sensor.hall_sensor_battery",
            "hall_sensor_battery",
            None,
            [_cell("c2", ReadingKind.PERCENTAGE, 100.0)],
        ),
    ]
    flag_suspicions(units)
    # "Hall" does NOT match "hall_sensor" (orphan stem), so no link_candidate.
    assert units[0].link_candidate is None


def test_link_candidate_exact_match_after_stem() -> None:
    """Orphan link candidates match when their stems (after removing suffixes) are equal."""
    units = [
        Unit("d1", "Living Room Heating", None, [_cell("c1", ReadingKind.NONE)]),
        Unit(
            "orphan:sensor.living_room_heating_battery",
            "living_room_heating_battery",
            None,
            [_cell("c2", ReadingKind.PERCENTAGE, 100.0)],
        ),
    ]
    flag_suspicions(units)
    # "Living Room Heating" normalised -> "living_room_heating"
    # orphan entity_id "sensor.living_room_heating_battery" -> stem "living_room_heating"
    # These match, so link_candidate is set.
    assert units[0].link_candidate == "orphan:sensor.living_room_heating_battery"


def test_unit_cannot_be_own_duplicate() -> None:
    """A unit is never flagged as its own duplicate_of."""
    units = [Unit("d1", "Sensor", None, [_cell("c1", ReadingKind.PERCENTAGE, 100.0)])]
    flag_suspicions(units)
    assert units[0].duplicate_of != "d1"
    assert units[0].duplicate_of is None


def test_unit_cannot_be_own_link_candidate() -> None:
    """A unit is never flagged as its own link_candidate."""
    units = [Unit("orphan:sensor.test", "test", None, [_cell("c1", ReadingKind.PERCENTAGE, 100.0)])]
    flag_suspicions(units)
    assert units[0].link_candidate != "orphan:sensor.test"
    assert units[0].link_candidate is None


def test_unit_with_no_cells() -> None:
    """A unit with no cells is handled safely."""
    units = [Unit("d1", "Empty Unit", None, [])]
    flag_suspicions(units)
    assert units[0].duplicate_of is None
    assert units[0].link_candidate is None
