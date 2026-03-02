from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from app.core.utils import now_utc

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent

logger = logging.getLogger(__name__)

_SIGNING_KEY: bytes | None = None
_KEY_LOADED: bool = False


def _get_signing_key() -> bytes | None:
    """Return the HMAC signing key from env, caching after first lookup."""
    global _SIGNING_KEY, _KEY_LOADED  # noqa: PLW0603
    if _KEY_LOADED:
        return _SIGNING_KEY
    raw = os.getenv("AUDIT_SIGNING_KEY")
    if not raw:
        logger.warning(
            "AUDIT_SIGNING_KEY not set — audit events will have no signature"
        )
        _KEY_LOADED = True
        return None
    _SIGNING_KEY = raw.encode("utf-8")
    _KEY_LOADED = True
    return _SIGNING_KEY


def _reset_signing_key_cache() -> None:
    """Reset the cached signing key — for testing only."""
    global _SIGNING_KEY, _KEY_LOADED  # noqa: PLW0603
    _SIGNING_KEY = None
    _KEY_LOADED = False


def compute_signature(checksum: str, key: bytes) -> bytes:
    """Compute HMAC-SHA256 of *checksum* using *key*."""
    return hmac.new(key, checksum.encode("utf-8"), hashlib.sha256).digest()


def verify_signature(checksum: str, signature: bytes, key: bytes) -> bool:
    """Constant-time comparison of expected vs actual HMAC."""
    expected = compute_signature(checksum, key)
    return hmac.compare_digest(expected, signature)


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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Audit event already exists",
            )
        checksum = hashlib.sha256(payload_raw.encode("utf-8")).hexdigest()

        signing_key = _get_signing_key()
        signature = compute_signature(checksum, signing_key) if signing_key else None

        audit_event = AuditEvent(
            id=event_id,
            timestamp_utc=now_utc(),
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            payload=payload_obj,
            checksum=checksum,
            signature=signature,
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
