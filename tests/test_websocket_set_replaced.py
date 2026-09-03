"""ws_set_replaced target validation and error handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from homeassistant.exceptions import ServiceNotFound

from custom_components.oikovis_pulse.battery_notes import (
    DOMAIN_BATTERY_NOTES,
    SERVICE_SET_BATTERY_REPLACED,
)
from custom_components.oikovis_pulse.websocket import _async_set_replaced


@dataclass
class _StubUser:
    is_admin: bool = True


@dataclass
class _StubConnection:
    user: _StubUser = field(default_factory=_StubUser)
    results: list[tuple[Any, Any]] = field(default_factory=list)
    errors: list[tuple[Any, str, str]] = field(default_factory=list)

    def send_result(self, msg_id: Any, result: Any = None) -> None:
        self.results.append((msg_id, result))

    def send_error(self, msg_id: Any, code: str, message: str) -> None:
        self.errors.append((msg_id, code, message))


class _StubServices:
    def __init__(self, *, raises: Exception | None = None) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self._raises = raises

    async def async_call(
        self, domain: str, service: str, payload: dict[str, Any], blocking: bool = True
    ) -> None:
        self.calls.append((domain, service, payload))
        if self._raises is not None:
            raise self._raises


class _StubHass:
    def __init__(self, *, raises: Exception | None = None) -> None:
        self.services = _StubServices(raises=raises)


@pytest.mark.asyncio
async def test_both_targets_errors_and_makes_no_service_call() -> None:
    hass = _StubHass()
    connection = _StubConnection()
    msg = {
        "id": 1,
        "source_entity_id": "sensor.foo_battery",
        "device_id": "device-1",
        "datetime_replaced": "2026-09-03T00:00:00+00:00",
    }

    await _async_set_replaced(hass, connection, msg)

    assert hass.services.calls == []
    assert connection.results == []
    assert len(connection.errors) == 1
    assert connection.errors[0][1] == "invalid_target"


@pytest.mark.asyncio
async def test_neither_target_errors_and_makes_no_service_call() -> None:
    hass = _StubHass()
    connection = _StubConnection()
    msg = {"id": 2, "datetime_replaced": "2026-09-03T00:00:00+00:00"}

    await _async_set_replaced(hass, connection, msg)

    assert hass.services.calls == []
    assert connection.results == []
    assert len(connection.errors) == 1
    assert connection.errors[0][1] == "invalid_target"


@pytest.mark.asyncio
async def test_exactly_one_target_calls_service_once_with_payload() -> None:
    hass = _StubHass()
    connection = _StubConnection()
    msg = {
        "id": 3,
        "source_entity_id": "sensor.foo_battery",
        "datetime_replaced": "2026-09-03T00:00:00+00:00",
    }

    await _async_set_replaced(hass, connection, msg)

    assert hass.services.calls == [
        (
            DOMAIN_BATTERY_NOTES,
            SERVICE_SET_BATTERY_REPLACED,
            {
                "datetime_replaced": "2026-09-03T00:00:00+00:00",
                "source_entity_id": "sensor.foo_battery",
            },
        )
    ]
    assert connection.errors == []
    assert connection.results == [(3, {"ok": True})]


@pytest.mark.asyncio
async def test_service_not_found_sends_error_not_success() -> None:
    hass = _StubHass(raises=ServiceNotFound(DOMAIN_BATTERY_NOTES, SERVICE_SET_BATTERY_REPLACED))
    connection = _StubConnection()
    msg = {
        "id": 4,
        "device_id": "device-1",
        "datetime_replaced": "2026-09-03T00:00:00+00:00",
    }

    await _async_set_replaced(hass, connection, msg)

    assert hass.services.calls  # the call was attempted
    assert connection.results == []
    assert len(connection.errors) == 1
    assert connection.errors[0][1] == "battery_notes_unavailable"
