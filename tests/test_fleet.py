"""Fleet assembly tests."""

from __future__ import annotations

from custom_components.oikovis_pulse.fleet import UnitMeta, build_fleet
from custom_components.oikovis_pulse.model import BatteryNote, CellClass, ReadingKind, SourceEntity
from custom_components.oikovis_pulse.store import StoredCell


def _entity(
    entity_id: str,
    device_id: str | None = "dev-1",
    unit: str | None = "%",
    state: str = "50",
    platform: str = "mqtt",
) -> SourceEntity:
    return SourceEntity(
        entity_id=entity_id,
        unique_id=f"uid-{entity_id}",
        platform=platform,
        device_id=device_id,
        device_class="battery",
        unit=unit,
        state=state,
    )


META = {"dev-1": UnitMeta(name="Hall Sensor", area_id="hall")}


def test_single_device_single_cell() -> None:
    fleet = build_fleet([_entity("sensor.hall_sensor_battery")], [], META, [])
    assert len(fleet) == 1
    assert fleet[0].name == "Hall Sensor"
    assert fleet[0].area_id == "hall"
    assert len(fleet[0].cells) == 1
    assert fleet[0].cells[0].reading_kind is ReadingKind.PERCENTAGE


def test_orphan_entity_becomes_its_own_unit() -> None:
    fleet = build_fleet([_entity("sensor.orphan_battery", device_id=None)], [], {}, [])
    assert len(fleet) == 1
    assert len(fleet[0].cells) == 1


def test_multi_cell_device_keeps_cells_separate() -> None:
    entities = [
        _entity("sensor.lock_battery", unit="%", state="18"),
        _entity("binary_sensor.lock_keypad_battery_critical", unit=None, state="off"),
    ]
    meta = {"dev-1": UnitMeta(name="Lock", area_id=None)}
    fleet = build_fleet(entities, [], meta, [])
    assert len(fleet[0].cells) == 2


def test_entity_level_note_metadata_lands_on_its_own_cell_only() -> None:
    entities = [
        _entity("sensor.lock_battery", unit="%", state="18"),
        _entity("binary_sensor.lock_keypad_battery_critical", unit=None, state="off"),
    ]
    notes = [
        BatteryNote(
            source_entity_id="binary_sensor.lock_keypad_battery_critical",
            device_id="dev-1",
            battery_type="AA",
            battery_quantity=2,
        )
    ]
    meta = {"dev-1": UnitMeta(name="Lock", area_id=None)}
    fleet = build_fleet(entities, notes, meta, [])
    typed = [c for c in fleet[0].cells if c.metadata.battery_type == "AA"]
    untyped = [c for c in fleet[0].cells if c.metadata.battery_type is None]
    assert len(typed) == 1
    assert len(untyped) == 1


def test_pulse_threshold_wins_over_battery_notes_but_both_are_kept() -> None:
    notes = [BatteryNote(source_entity_id=None, device_id="dev-1", low_threshold=15.0)]
    fleet = build_fleet([_entity("sensor.hall_sensor_battery")], notes, META, [])
    cell = fleet[0].cells[0]
    assert cell.metadata.low_threshold == 20.0
    assert cell.metadata.bn_low_threshold == 15.0


def test_built_in_classification_is_applied() -> None:
    entity = _entity("sensor.phone_battery", platform="mobile_app")
    meta = {"dev-1": UnitMeta(name="Phone", area_id=None)}
    fleet = build_fleet([entity], [], meta, [])
    assert fleet[0].cells[0].cell_class is CellClass.BUILT_IN


def test_stored_identity_is_reused_across_rebuilds() -> None:
    entities = [_entity("sensor.hall_sensor_battery")]
    first = build_fleet(entities, [], META, [])
    original_id = first[0].cells[0].cell_id

    stored = [StoredCell(cell_id=original_id, member_unique_ids=["uid-sensor.hall_sensor_battery"])]
    second = build_fleet(entities, [], META, stored)
    assert second[0].cells[0].cell_id == original_id


def test_empty_input_returns_empty_list() -> None:
    assert build_fleet([], [], {}, []) == []


def test_stored_id_collision_only_one_cell_claims_it() -> None:
    """A stored cell held members {a, b}; rebuild now produces two separate
    cells, one with {a} and one with {b}. Both resolve to the same stored id
    via resolve_cell_id; only the higher-overlap one may keep it (here it's a
    tie by overlap=1 each, so the tiebreak is smallest sorted member set)."""
    entities = [
        _entity("sensor.lock_battery_a", unit="%", state="10"),
        _entity("sensor.lock_battery_b", unit="%", state="20"),
    ]
    # Force each entity into its own cell via entity-level notes so grouping
    # does not merge them by stem.
    notes = [
        BatteryNote(source_entity_id="sensor.lock_battery_a", device_id="dev-1"),
        BatteryNote(source_entity_id="sensor.lock_battery_b", device_id="dev-1"),
    ]
    stored = [
        StoredCell(
            cell_id="stored-1",
            member_unique_ids=["uid-sensor.lock_battery_a", "uid-sensor.lock_battery_b"],
        )
    ]
    meta = {"dev-1": UnitMeta(name="Lock", area_id=None)}
    fleet = build_fleet(entities, notes, meta, stored)
    cell_ids = [c.cell_id for c in fleet[0].cells]
    assert cell_ids.count("stored-1") == 1
    assert len(set(cell_ids)) == 2

    # The winner is the cell whose sorted member unique_ids compare smallest:
    # uid-sensor.lock_battery_a < uid-sensor.lock_battery_b
    winner = next(c for c in fleet[0].cells if c.cell_id == "stored-1")
    assert winner.members == ("uid-sensor.lock_battery_a",)


def test_ambiguous_device_note_resolves_to_no_cell() -> None:
    entities = [
        _entity("sensor.lock_battery_a", unit="%", state="10"),
        _entity("sensor.lock_battery_b", unit="%", state="20"),
    ]
    notes = [
        BatteryNote(source_entity_id="sensor.lock_battery_a", device_id="dev-1"),
        BatteryNote(source_entity_id="sensor.lock_battery_b", device_id="dev-1"),
        BatteryNote(source_entity_id=None, device_id="dev-1", battery_type="AA"),
    ]
    meta = {"dev-1": UnitMeta(name="Something Else Entirely", area_id=None)}
    fleet = build_fleet(entities, notes, meta, [])
    assert fleet[0].unresolved_note is True
    assert all(c.metadata.battery_type is None for c in fleet[0].cells)


def test_missing_units_meta_falls_back_to_entity_derived_name() -> None:
    fleet = build_fleet([_entity("sensor.hall_sensor_battery")], [], {}, [])
    assert len(fleet) == 1
    assert fleet[0].name
    assert fleet[0].area_id is None


def test_all_members_unavailable_cell_still_appears() -> None:
    entity = _entity("sensor.hall_sensor_battery", state="unavailable")
    fleet = build_fleet([entity], [], META, [])
    assert len(fleet[0].cells) == 1
    assert fleet[0].cells[0].reading_kind is ReadingKind.NONE


def test_entity_level_note_wins_whole_cell_over_device_level_threshold() -> None:
    """The primary cell already carries an entity-level note (its own
    low_threshold). A device-level note on the same device carries a
    different threshold. The entity-level note must win the whole cell,
    including bn_low_threshold — not just battery_type/quantity/last_replaced."""
    entities = [
        _entity("sensor.lock_battery", unit="%", state="18"),
        _entity("binary_sensor.lock_keypad_battery_critical", unit=None, state="off"),
    ]
    notes = [
        BatteryNote(
            source_entity_id="sensor.lock_battery",
            device_id="dev-1",
            battery_type="CR2032",
            low_threshold=10.0,
        ),
        BatteryNote(source_entity_id=None, device_id="dev-1", low_threshold=15.0),
    ]
    meta = {"dev-1": UnitMeta(name="Lock", area_id=None)}
    fleet = build_fleet(entities, notes, meta, [])
    primary = next(c for c in fleet[0].cells if c.reading_kind is ReadingKind.PERCENTAGE)
    assert primary.metadata.battery_type == "CR2032"
    assert primary.metadata.bn_low_threshold == 10.0
    assert primary.metadata.low_threshold == 20.0


def test_device_level_note_threshold_applies_when_no_entity_level_note() -> None:
    """The primary cell has no entity-level note. The device-level note's
    threshold must still be applied (the fix must not simply disable it)."""
    entities = [
        _entity("sensor.lock_battery", unit="%", state="18"),
        _entity("binary_sensor.lock_keypad_battery_critical", unit=None, state="off"),
    ]
    notes = [BatteryNote(source_entity_id=None, device_id="dev-1", low_threshold=15.0)]
    meta = {"dev-1": UnitMeta(name="Lock", area_id=None)}
    fleet = build_fleet(entities, notes, meta, [])
    primary = next(c for c in fleet[0].cells if c.reading_kind is ReadingKind.PERCENTAGE)
    assert primary.metadata.bn_low_threshold == 15.0
    assert primary.metadata.low_threshold == 20.0


def test_inputs_are_not_mutated() -> None:
    entities = [_entity("sensor.hall_sensor_battery")]
    notes = [BatteryNote(source_entity_id=None, device_id="dev-1", low_threshold=15.0)]
    units_meta = dict(META)
    stored: list[StoredCell] = []

    entities_copy = list(entities)
    notes_copy = list(notes)
    units_meta_copy = dict(units_meta)
    stored_copy = list(stored)

    build_fleet(entities, notes, units_meta, stored)

    assert entities == entities_copy
    assert notes == notes_copy
    assert units_meta == units_meta_copy
    assert stored == stored_copy
