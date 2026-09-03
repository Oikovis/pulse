"""Summary sensor arithmetic."""

from __future__ import annotations

from custom_components.oikovis_pulse.model import Cell, CellClass, CellMetadata, ReadingKind, Unit
from custom_components.oikovis_pulse.websocket import serialise_fleet, summarise


def _cell(
    cell_id: str,
    *,
    percentage: float | None = None,
    kind: ReadingKind = ReadingKind.PERCENTAGE,
    low: bool = False,
    critical: bool = False,
    charging: bool = False,
    cell_class: CellClass = CellClass.REPLACEABLE,
    threshold: float = 20.0,
) -> Cell:
    return Cell(
        cell_id=cell_id,
        members=(f"uid-{cell_id}",),
        reading_kind=kind,
        percentage=percentage,
        low=low,
        critical=critical,
        charging=charging,
        cell_class=cell_class,
        metadata=CellMetadata(low_threshold=threshold),
    )


def _unit(*cells: Cell) -> Unit:
    return Unit(unit_id="u1", name="Unit", area_id=None, cells=list(cells))


def test_low_counts_replaceable_below_threshold() -> None:
    units = [_unit(_cell("c1", percentage=10.0), _cell("c2", percentage=90.0))]
    assert summarise(units)["cells_low"] == 1


def test_built_in_cells_are_never_counted() -> None:
    units = [_unit(_cell("c1", percentage=5.0, cell_class=CellClass.BUILT_IN))]
    counts = summarise(units)
    assert counts["cells_low"] == 0
    assert counts["cells_needing_attention"] == 0


def test_charging_cells_are_never_counted() -> None:
    units = [_unit(_cell("c1", percentage=5.0, charging=True))]
    assert summarise(units)["cells_needing_attention"] == 0


def test_critical_flag_counts_even_above_threshold() -> None:
    units = [_unit(_cell("c1", percentage=80.0, critical=True))]
    assert summarise(units)["cells_critical"] == 1


def test_without_reading_excludes_non_replaceable() -> None:
    units = [
        _unit(
            _cell("c1", kind=ReadingKind.NONE),
            _cell("c2", kind=ReadingKind.NONE, cell_class=CellClass.EXCLUDED),
        )
    ]
    assert summarise(units)["cells_without_reading"] == 1


def test_needing_attention_is_a_union_without_double_counting() -> None:
    units = [_unit(_cell("c1", percentage=5.0, critical=True))]
    assert summarise(units)["cells_needing_attention"] == 1


def test_serialise_round_trips_key_fields() -> None:
    payload = serialise_fleet([_unit(_cell("c1", percentage=42.0))])
    assert payload[0]["cells"][0]["cell_id"] == "c1"
    assert payload[0]["cells"][0]["percentage"] == 42.0
    assert payload[0]["cells"][0]["cell_class"] == "replaceable"
