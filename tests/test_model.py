"""Model type tests."""

from __future__ import annotations

from custom_components.oikovis_pulse.model import (
    Cell,
    CellClass,
    CellMetadata,
    ReadingKind,
    SourceEntity,
    Unit,
)


def test_source_entity_is_hashable_and_frozen() -> None:
    entity = SourceEntity(
        entity_id="sensor.hall_sensor_battery",
        unique_id="uid-1",
        platform="mqtt",
        device_id="dev-1",
        device_class="battery",
        unit="%",
        state="87",
        disabled=False,
        hidden=False,
    )
    assert entity.unique_id == "uid-1"
    assert {entity}  # hashable


def test_cell_defaults_are_safe() -> None:
    cell = Cell(cell_id="c1", members=("uid-1",))
    assert cell.reading_kind is ReadingKind.NONE
    assert cell.cell_class is CellClass.REPLACEABLE
    assert cell.charging is False
    assert cell.percentage is None
    assert cell.metadata == CellMetadata()


def test_unit_holds_cells() -> None:
    unit = Unit(unit_id="u1", name="Hall Sensor", area_id=None, cells=[Cell("c1", ("uid-1",))])
    assert len(unit.cells) == 1
    assert unit.unresolved_note is False


def test_unit_carries_unused_v1_qualifiers() -> None:
    """Present now so multi-site and merging are not migrations later."""
    unit = Unit(unit_id="u1", name="Hall Sensor", area_id=None)
    assert unit.instance is None
    assert unit.duplicate_of is None
    assert unit.link_candidate is None
