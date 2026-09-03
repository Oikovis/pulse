"""Coordinator store round-trip tests, using a stub Store rather than a live hass.

`PulseCoordinator.async_load_store` and `async_save_store` only touch
`self._store` and `self._stored`, never `self.hass`, so a coordinator
instance is built with `object.__new__` and those two attributes set
directly rather than going through `DataUpdateCoordinator.__init__`, which
needs a real Home Assistant instance.
"""

from __future__ import annotations

from custom_components.oikovis_pulse.coordinator import PulseCoordinator
from custom_components.oikovis_pulse.model import Cell, ReadingKind, Unit
from custom_components.oikovis_pulse.store import StoredCell


class _StubStore:
    """Fake Store with the two async methods the coordinator calls."""

    def __init__(self, payload: object = None) -> None:
        self.payload = payload
        self.saved: dict | None = None

    async def async_load(self):
        return self.payload

    async def async_save(self, data: dict) -> None:
        self.saved = data


def _make_coordinator(store_payload: object = None) -> PulseCoordinator:
    coordinator = object.__new__(PulseCoordinator)
    coordinator._store = _StubStore(store_payload)
    coordinator._stored = []
    return coordinator


def _cell(cell_id: str, member: str) -> Cell:
    return Cell(cell_id=cell_id, members=(member,), reading_kind=ReadingKind.PERCENTAGE)


async def test_unknown_extra_key_in_stored_record_is_tolerated() -> None:
    payload = {
        "cells": [
            {
                "cell_id": "a",
                "member_unique_ids": ["uid-a"],
                "class_override": None,
                "metadata": {},
                "gone_since": None,
                "bogus_future_field": "whatever",
            }
        ]
    }
    coordinator = _make_coordinator(payload)
    await coordinator.async_load_store()
    assert len(coordinator._stored) == 1
    assert coordinator._stored[0].cell_id == "a"
    assert coordinator._stored[0].member_unique_ids == ["uid-a"]


async def test_malformed_record_is_skipped_good_record_survives() -> None:
    payload = {
        "cells": [
            {"cell_id": "good", "member_unique_ids": ["uid-good"]},
            {"member_unique_ids": ["uid-bad"]},  # missing required cell_id
        ]
    }
    coordinator = _make_coordinator(payload)
    await coordinator.async_load_store()
    assert [c.cell_id for c in coordinator._stored] == ["good"]


async def test_malformed_store_payload_degrades_to_empty_list() -> None:
    coordinator = _make_coordinator("not-even-a-dict-shaped-payload")
    # async_load returning a truthy non-dict: .get() would raise AttributeError,
    # which async_load_store must not propagate.
    coordinator._store.payload = ["not", "a", "dict"]
    await coordinator.async_load_store()
    assert coordinator._stored == []


async def test_cell_absent_from_fresh_fleet_gains_gone_since() -> None:
    coordinator = _make_coordinator()
    coordinator._stored = [
        StoredCell(cell_id="vanished", member_unique_ids=["uid-x"], metadata={"k": "v"})
    ]
    units: list[Unit] = []  # nothing in the fresh fleet
    await coordinator.async_save_store(units)
    record = next(c for c in coordinator._stored if c.cell_id == "vanished")
    assert record.gone_since is not None
    assert record.metadata == {"k": "v"}
    assert record.class_override is None


async def test_existing_gone_since_is_not_overwritten() -> None:
    coordinator = _make_coordinator()
    coordinator._stored = [
        StoredCell(
            cell_id="vanished", member_unique_ids=["uid-x"], gone_since="2020-01-01T00:00:00+00:00"
        )
    ]
    await coordinator.async_save_store([])
    record = next(c for c in coordinator._stored if c.cell_id == "vanished")
    assert record.gone_since == "2020-01-01T00:00:00+00:00"


async def test_reappearing_cell_clears_gone_since() -> None:
    coordinator = _make_coordinator()
    coordinator._stored = [
        StoredCell(
            cell_id="back-again",
            member_unique_ids=["uid-y"],
            gone_since="2020-01-01T00:00:00+00:00",
        )
    ]
    unit = Unit(unit_id="dev-1", name="Dev 1", area_id=None, cells=[_cell("back-again", "uid-y")])
    await coordinator.async_save_store([unit])
    record = next(c for c in coordinator._stored if c.cell_id == "back-again")
    assert record.gone_since is None
