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
