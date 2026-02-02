from __future__ import annotations

import base64
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models.audit import AuditEvent
from app.schemas.audit import AuditEventListResponse, AuditEventRead


router = APIRouter()


def _encode_cursor(timestamp: datetime, event_id: UUID) -> str:
    raw = f"{timestamp.isoformat()}|{event_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
    timestamp_str, event_id_str = decoded.split("|", maxsplit=1)
    return datetime.fromisoformat(timestamp_str), UUID(event_id_str)


@router.get("/events", response_model=AuditEventListResponse)
def list_audit_events(
    entity_type: str | None = Query(None),
    entity_id: UUID | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> AuditEventListResponse:
    query = session.query(AuditEvent)
    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditEvent.entity_id == entity_id)
    if start:
        query = query.filter(AuditEvent.timestamp_utc >= start)
    if end:
        query = query.filter(AuditEvent.timestamp_utc <= end)

    if cursor:
        cursor_timestamp, cursor_id = _decode_cursor(cursor)
        query = query.filter(
            (AuditEvent.timestamp_utc > cursor_timestamp)
            | ((AuditEvent.timestamp_utc == cursor_timestamp) & (AuditEvent.id > cursor_id))
        )

    rows = (
        query.order_by(AuditEvent.timestamp_utc.asc(), AuditEvent.id.asc())
        .limit(limit + 1)
        .all()
    )

    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = _encode_cursor(last.timestamp_utc, last.id)
        rows = rows[:limit]

    return AuditEventListResponse(
        events=[AuditEventRead.model_validate(row) for row in rows],
        next_cursor=next_cursor,
    )