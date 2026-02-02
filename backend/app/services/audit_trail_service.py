from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


class AuditTrailService:
    @staticmethod
    def record(
        db: Session,
        *,
        event_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        event_type: str,
        payload_raw: str,
        payload_obj: object,
    ) -> AuditEvent:
        existing = db.get(AuditEvent, event_id)
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Audit event already exists")
        checksum = hashlib.sha256(payload_raw.encode("utf-8")).hexdigest()
        audit_event = AuditEvent(
            id=event_id,
            timestamp_utc=datetime.now(timezone.utc),
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            payload=payload_obj,
            checksum=checksum,
        )
        db.add(audit_event)
        db.commit()
        db.refresh(audit_event)
        return audit_event


def normalize_payload_raw(payload: object | None) -> tuple[str, object]:
    if payload is None:
        return "null", None
    payload_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return payload_raw, payload