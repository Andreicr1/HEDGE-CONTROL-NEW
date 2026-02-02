from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import status

from app.models.audit import AuditEvent


def test_audit_query_filters(session, client) -> None:
    now = datetime.now(timezone.utc)
    order_id = uuid4()
    contract_id = uuid4()

    session.add(
        AuditEvent(
            id=uuid4(),
            entity_type="order",
            entity_id=order_id,
            event_type="created",
            payload={"example": 1},
            checksum="".ljust(64, "0"),
            timestamp_utc=now - timedelta(hours=1),
        )
    )
    session.add(
        AuditEvent(
            id=uuid4(),
            entity_type="hedge_contract",
            entity_id=contract_id,
            event_type="created",
            payload={"example": 2},
            checksum="".ljust(64, "0"),
            timestamp_utc=now,
        )
    )
    session.commit()

    by_entity = client.get(
        "/audit/events",
        params={
            "entity_type": "order",
            "entity_id": str(order_id),
        },
    )
    assert by_entity.status_code == status.HTTP_200_OK
    assert len(by_entity.json()["events"]) == 1

    by_range = client.get(
        "/audit/events",
        params={
            "start": (now - timedelta(minutes=30)).isoformat(),
            "end": (now + timedelta(minutes=30)).isoformat(),
        },
    )
    assert by_range.status_code == status.HTTP_200_OK
    assert len(by_range.json()["events"]) == 1