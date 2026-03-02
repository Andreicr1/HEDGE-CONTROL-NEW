"""Tests for audit trail HMAC signature (Item 2.4).

Validates:
* With AUDIT_SIGNING_KEY set, recorded events include a valid HMAC-SHA256 signature.
* Without the key, events are recorded with signature = None (graceful degradation).
* GET /audit/events/{id}/verify validates signatures correctly.
* Tampered checksums are detected.
"""

from __future__ import annotations

import hashlib
import os
import uuid

import pytest
from fastapi import status

from app.services.audit_trail_service import (
    AuditTrailService,
    _get_signing_key,
    _reset_signing_key_cache,
    compute_signature,
    verify_signature,
)

TEST_KEY = "test-signing-key-for-audit-hmac"


@pytest.fixture(autouse=True)
def _reset_key_cache():
    """Reset the module-level signing-key cache before and after each test."""
    _reset_signing_key_cache()
    yield
    _reset_signing_key_cache()
    # Remove env var so it doesn't leak
    os.environ.pop("AUDIT_SIGNING_KEY", None)


# ── Unit tests for HMAC helpers ───────────────────────────────────────
class TestHMACHelpers:
    def test_compute_and_verify_roundtrip(self) -> None:
        key = TEST_KEY.encode("utf-8")
        checksum = hashlib.sha256(b"some payload").hexdigest()
        sig = compute_signature(checksum, key)
        assert isinstance(sig, bytes)
        assert len(sig) == 32  # SHA-256 → 32 bytes
        assert verify_signature(checksum, sig, key)

    def test_wrong_key_fails_verification(self) -> None:
        key = TEST_KEY.encode("utf-8")
        checksum = hashlib.sha256(b"payload").hexdigest()
        sig = compute_signature(checksum, key)
        assert not verify_signature(checksum, sig, b"wrong-key")

    def test_tampered_checksum_fails_verification(self) -> None:
        key = TEST_KEY.encode("utf-8")
        checksum = hashlib.sha256(b"original").hexdigest()
        sig = compute_signature(checksum, key)
        tampered = hashlib.sha256(b"tampered").hexdigest()
        assert not verify_signature(tampered, sig, key)


# ── Service-level tests ──────────────────────────────────────────────
class TestAuditSignatureService:
    def test_record_with_key_populates_signature(self, session) -> None:
        os.environ["AUDIT_SIGNING_KEY"] = TEST_KEY
        event = AuditTrailService.record(
            session,
            event_id=uuid.uuid4(),
            entity_type="order",
            entity_id=uuid.uuid4(),
            event_type="created",
            payload_raw="{}",
            payload_obj={},
        )
        assert event.signature is not None
        assert len(event.signature) == 32
        # Verify the signature matches the checksum
        key = _get_signing_key()
        assert key is not None
        assert verify_signature(event.checksum, event.signature, key)

    def test_record_without_key_signature_is_none(self, session) -> None:
        os.environ.pop("AUDIT_SIGNING_KEY", None)
        event = AuditTrailService.record(
            session,
            event_id=uuid.uuid4(),
            entity_type="order",
            entity_id=uuid.uuid4(),
            event_type="created",
            payload_raw="{}",
            payload_obj={},
        )
        assert event.signature is None


# ── Endpoint tests ────────────────────────────────────────────────────
class TestAuditVerifyEndpoint:
    def test_verify_valid_signature(self, client) -> None:
        os.environ["AUDIT_SIGNING_KEY"] = TEST_KEY
        # Create an order to trigger an audit event
        resp = client.post(
            "/orders/sales", json={"price_type": "variable", "quantity_mt": 5.0}
        )
        assert resp.status_code == status.HTTP_201_CREATED
        order_id = resp.json()["id"]

        # Fetch the audit event
        events_resp = client.get(
            "/audit/events", params={"entity_type": "order", "entity_id": order_id}
        )
        assert events_resp.status_code == 200
        events = events_resp.json()["events"]
        assert len(events) >= 1
        event_id = events[0]["id"]

        # Verify
        verify_resp = client.get(f"/audit/events/{event_id}/verify")
        assert verify_resp.status_code == 200
        body = verify_resp.json()
        assert body["valid"] is True
        assert body["event_id"] == event_id

    def test_verify_nonexistent_event_404(self, client) -> None:
        os.environ["AUDIT_SIGNING_KEY"] = TEST_KEY
        resp = client.get(f"/audit/events/{uuid.uuid4()}/verify")
        assert resp.status_code == 404

    def test_verify_without_key_returns_503(self, client) -> None:
        os.environ.pop("AUDIT_SIGNING_KEY", None)
        # Create an order (no signature will be stored)
        resp = client.post(
            "/orders/sales", json={"price_type": "variable", "quantity_mt": 5.0}
        )
        assert resp.status_code == status.HTTP_201_CREATED
        order_id = resp.json()["id"]

        events_resp = client.get(
            "/audit/events", params={"entity_type": "order", "entity_id": order_id}
        )
        events = events_resp.json()["events"]
        event_id = events[0]["id"]

        verify_resp = client.get(f"/audit/events/{event_id}/verify")
        assert verify_resp.status_code == 503

    def test_verify_unsigned_event_reports_invalid(self, client) -> None:
        # Create event without key
        os.environ.pop("AUDIT_SIGNING_KEY", None)
        resp = client.post(
            "/orders/sales", json={"price_type": "variable", "quantity_mt": 5.0}
        )
        order_id = resp.json()["id"]

        events_resp = client.get(
            "/audit/events", params={"entity_type": "order", "entity_id": order_id}
        )
        event_id = events_resp.json()["events"][0]["id"]

        # Now set the key and verify — event has no signature
        _reset_signing_key_cache()
        os.environ["AUDIT_SIGNING_KEY"] = TEST_KEY
        verify_resp = client.get(f"/audit/events/{event_id}/verify")
        assert verify_resp.status_code == 200
        body = verify_resp.json()
        assert body["valid"] is False
        assert "without a signature" in body["detail"]
