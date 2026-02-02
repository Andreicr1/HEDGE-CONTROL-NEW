from __future__ import annotations

import uuid

import pytest
from fastapi import status
from fastapi import HTTPException

from app.services.audit_trail_service import AuditTrailService


def test_audit_event_insert_idempotent_conflict(session) -> None:
    event_id = uuid.uuid4()
    payload_raw = "{}"

    AuditTrailService.record(
        session,
        event_id=event_id,
        entity_type="order",
        entity_id=uuid.uuid4(),
        event_type="created",
        payload_raw=payload_raw,
        payload_obj={},
    )

    with pytest.raises(HTTPException) as excinfo:
        AuditTrailService.record(
            session,
            event_id=event_id,
            entity_type="order",
            entity_id=uuid.uuid4(),
            event_type="created",
            payload_raw=payload_raw,
            payload_obj={},
        )
    assert excinfo.value.status_code == status.HTTP_409_CONFLICT


def test_audit_dependency_records_on_success(client) -> None:
    order_payload = {"price_type": "variable", "quantity_mt": 5.0}
    response = client.post("/orders/sales", json=order_payload)
    assert response.status_code == status.HTTP_201_CREATED
    order_id = response.json()["id"]

    events = client.get("/audit/events", params={"entity_type": "order", "entity_id": order_id})
    assert events.status_code == status.HTTP_200_OK
    assert events.json()["events"]