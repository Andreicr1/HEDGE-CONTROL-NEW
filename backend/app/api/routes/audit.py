from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.core.database import get_session
from app.core.pagination import paginate
from app.models.audit import AuditEvent
from app.schemas.audit import AuditEventListResponse, AuditEventRead
from app.services.audit_trail_service import _get_signing_key, verify_signature


router = APIRouter()


class AuditVerifyResponse(BaseModel):
    event_id: UUID
    valid: bool
    detail: str


@router.get("/events", response_model=AuditEventListResponse)
def list_audit_events(
    entity_type: str | None = Query(None),
    entity_id: UUID | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _: None = Depends(require_role("auditor")),
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

    rows, next_cursor = paginate(
        query,
        created_at_col=AuditEvent.timestamp_utc,
        id_col=AuditEvent.id,
        cursor=cursor,
        limit=limit,
        ts_attr="timestamp_utc",
    )

    return AuditEventListResponse(
        events=[AuditEventRead.model_validate(row) for row in rows],
        next_cursor=next_cursor,
    )


@router.get("/events/{event_id}/verify", response_model=AuditVerifyResponse)
def verify_audit_event(
    event_id: UUID,
    _: None = Depends(require_role("auditor")),
    session: Session = Depends(get_session),
) -> AuditVerifyResponse:
    """Verify the HMAC signature of an audit event."""
    event = session.get(AuditEvent, event_id)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audit event not found"
        )

    key = _get_signing_key()
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AUDIT_SIGNING_KEY not configured — verification unavailable",
        )

    if event.signature is None:
        return AuditVerifyResponse(
            event_id=event_id,
            valid=False,
            detail="Event was recorded without a signature",
        )

    valid = verify_signature(event.checksum, event.signature, key)
    return AuditVerifyResponse(
        event_id=event_id,
        valid=valid,
        detail="Signature valid"
        if valid
        else "Signature mismatch — event may have been tampered with",
    )
