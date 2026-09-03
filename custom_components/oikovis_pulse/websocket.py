"""WebSocket surface and summary arithmetic."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound

from .battery_notes import DOMAIN_BATTERY_NOTES, SERVICE_SET_BATTERY_REPLACED
from .const import DATA_COORDINATOR, DOMAIN
from .model import Cell, CellClass, ReadingKind, Unit

_LOGGER = logging.getLogger(__name__)


def _countable(cell: Cell) -> bool:
    """Only replaceable, non-charging, non-gone cells enter any summary."""
    return (
        cell.cell_class is CellClass.REPLACEABLE and not cell.charging and cell.gone_since is None
    )


def summarise(units: Sequence[Unit]) -> dict[str, int]:
    """Count the four published summary figures."""
    low: set[str] = set()
    critical: set[str] = set()
    without_reading: set[str] = set()

    for unit in units:
        for cell in unit.cells:
            if not _countable(cell):
                continue
            threshold = cell.metadata.low_threshold or 20.0
            if cell.reading_kind is ReadingKind.NONE:
                without_reading.add(cell.cell_id)
                continue
            if cell.critical or (cell.percentage is not None and cell.percentage <= threshold / 2):
                critical.add(cell.cell_id)
            if cell.low or (cell.percentage is not None and cell.percentage <= threshold):
                low.add(cell.cell_id)

    return {
        "cells_low": len(low),
        "cells_critical": len(critical),
        "cells_without_reading": len(without_reading),
        "cells_needing_attention": len(low | critical | without_reading),
    }


def serialise_fleet(units: Sequence[Unit]) -> list[dict[str, Any]]:
    """Convert the fleet to JSON-safe dictionaries for the panel."""
    return [asdict(unit) for unit in units]


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    """Register Pulse's WebSocket commands."""
    websocket_api.async_register_command(hass, ws_fleet)
    websocket_api.async_register_command(hass, ws_set_replaced)


@websocket_api.websocket_command({vol.Required("type"): "oikovis_pulse/fleet"})
@websocket_api.async_response
async def ws_fleet(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the whole fleet plus its summary counts."""
    entries = hass.data.get(DOMAIN, {})
    coordinator = next(
        (data[DATA_COORDINATOR] for data in entries.values() if DATA_COORDINATOR in data),
        None,
    )
    if coordinator is None:
        connection.send_error(msg["id"], "not_ready", "Pulse is not set up")
        return
    units = coordinator.data or []
    connection.send_result(
        msg["id"],
        {"units": serialise_fleet(units), "summary": summarise(units)},
    )


async def _async_set_replaced(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Record a battery replacement through Battery Notes.

    Undecorated so it can be exercised directly in tests with a stub
    connection/hass, without going through HA's background-task scheduling.
    """
    source_entity_id = msg.get("source_entity_id")
    device_id = msg.get("device_id")

    if bool(source_entity_id) == bool(device_id):
        connection.send_error(
            msg["id"],
            "invalid_target",
            "Exactly one of source_entity_id or device_id must be given",
        )
        return

    payload = {"datetime_replaced": msg["datetime_replaced"]}
    if source_entity_id:
        payload["source_entity_id"] = source_entity_id
    else:
        payload["device_id"] = device_id

    try:
        await hass.services.async_call(
            DOMAIN_BATTERY_NOTES, SERVICE_SET_BATTERY_REPLACED, payload, blocking=True
        )
    except ServiceNotFound:
        _LOGGER.warning("Battery Notes is not installed; cannot record replacement")
        connection.send_error(
            msg["id"], "battery_notes_unavailable", "The Battery Notes integration is not available"
        )
        return
    except HomeAssistantError as err:
        _LOGGER.warning("Failed to record battery replacement: %s", err)
        connection.send_error(msg["id"], "battery_notes_error", str(err))
        return

    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "oikovis_pulse/set_replaced",
        vol.Optional("source_entity_id"): str,
        vol.Optional("device_id"): str,
        vol.Required("datetime_replaced"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_set_replaced(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """WebSocket entry point for recording a battery replacement."""
    await _async_set_replaced(hass, connection, msg)
