"""Tests for Hedge Model + CRUD — component 1.4."""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.counterparty import Counterparty
from app.models.exposure import (
    Exposure,
    ExposureStatus,
    ExposureDirection,
    ExposureSourceType,
)
from app.models.rfqs import RFQ, RFQState, RFQDirection, RFQIntent


ENDPOINT = "/hedges"


def _create_counterparty(session: Session) -> uuid.UUID:
    """Insert a counterparty directly and return its id."""
    cp = Counterparty(
        type="customer",
        name=f"Cpty-{uuid.uuid4().hex[:6]}",
        country="BRA",
    )
    session.add(cp)
    session.commit()
    session.refresh(cp)
    return cp.id


def _create_exposure(
    session: Session, direction: str = "long", tons: float = 100.0
) -> uuid.UUID:
    """Insert an exposure directly for linking tests."""
    exp = Exposure(
        commodity="ALUMINUM",
        direction=ExposureDirection(direction),
        source_type=ExposureSourceType.sales_order,
        source_id=uuid.uuid4(),
        original_tons=tons,
        open_tons=tons,
        status=ExposureStatus.open,
    )
    session.add(exp)
    session.commit()
    session.refresh(exp)
    return exp.id


def _create_rfq(session: Session, state: RFQState = RFQState.awarded) -> uuid.UUID:
    """Insert an RFQ directly for from-rfq tests."""
    rfq = RFQ(
        rfq_number=f"RFQ-{uuid.uuid4().hex[:8]}",
        intent=RFQIntent.commercial_hedge,
        commodity="ALUMINUM",
        quantity_mt=50.0,
        delivery_window_start=date(2025, 7, 1),
        delivery_window_end=date(2025, 9, 30),
        direction=RFQDirection.buy,
        commercial_active_mt=50,
        commercial_passive_mt=0,
        commercial_net_mt=50,
        commercial_reduction_applied_mt=0,
        exposure_snapshot_timestamp=datetime.now(timezone.utc),
        state=state,
    )
    session.add(rfq)
    session.commit()
    session.refresh(rfq)
    return rfq.id


def _make_hedge_payload(counterparty_id: uuid.UUID, **overrides) -> dict:
    base = {
        "counterparty_id": str(counterparty_id),
        "commodity": "ALUMINUM",
        "direction": "buy",
        "tons": 100.0,
        "price_per_ton": 2450.50,
        "premium_discount": 5.0,
        "settlement_date": "2025-09-30",
        "source_type": "manual",
    }
    base.update(overrides)
    return base


# -----------------------------------------------------------------------
# CREATE
# -----------------------------------------------------------------------


class TestCreateHedge:
    def test_create_hedge_success(self, client, session):
        cp_id = _create_counterparty(session)
        payload = _make_hedge_payload(cp_id)
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 201
        body = r.json()
        assert body["commodity"] == "ALUMINUM"
        assert body["direction"] == "buy"
        assert body["tons"] == 100.0
        assert body["price_per_ton"] == 2450.50
        assert body["status"] == "active"
        assert body["reference"].startswith("H-")

    def test_create_hedge_with_exposure_link(self, client, session):
        cp_id = _create_counterparty(session)
        exp_id = _create_exposure(session, "long", 200.0)
        payload = _make_hedge_payload(cp_id, exposure_id=str(exp_id), tons=80.0)
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 201
        # Exposure open_tons should be reduced
        exp = session.query(Exposure).filter(Exposure.id == exp_id).first()
        assert exp.open_tons == pytest.approx(120.0)
        assert exp.status == ExposureStatus.partially_hedged

    def test_create_hedge_fully_hedges_exposure(self, client, session):
        cp_id = _create_counterparty(session)
        exp_id = _create_exposure(session, "long", 50.0)
        payload = _make_hedge_payload(cp_id, exposure_id=str(exp_id), tons=50.0)
        r = client.post(ENDPOINT, json=payload)
        assert r.status_code == 201
        exp = session.query(Exposure).filter(Exposure.id == exp_id).first()
        assert exp.open_tons == pytest.approx(0.0)
        assert exp.status == ExposureStatus.fully_hedged


# -----------------------------------------------------------------------
# LIST
# -----------------------------------------------------------------------


class TestListHedges:
    def test_list_empty(self, client):
        r = client.get(ENDPOINT)
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_list_returns_created(self, client, session):
        cp_id = _create_counterparty(session)
        client.post(ENDPOINT, json=_make_hedge_payload(cp_id))
        client.post(ENDPOINT, json=_make_hedge_payload(cp_id, direction="sell"))
        r = client.get(ENDPOINT)
        assert r.status_code == 200
        assert len(r.json()["items"]) == 2

    def test_list_filter_by_commodity(self, client, session):
        cp_id = _create_counterparty(session)
        client.post(ENDPOINT, json=_make_hedge_payload(cp_id, commodity="ALUMINUM"))
        client.post(ENDPOINT, json=_make_hedge_payload(cp_id, commodity="COPPER"))
        r = client.get(ENDPOINT, params={"commodity": "COPPER"})
        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["commodity"] == "COPPER"

    def test_list_filter_by_status(self, client, session):
        cp_id = _create_counterparty(session)
        client.post(ENDPOINT, json=_make_hedge_payload(cp_id))
        r = client.get(ENDPOINT, params={"status": "active"})
        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "active"

        r2 = client.get(ENDPOINT, params={"status": "settled"})
        assert r2.json()["items"] == []


# -----------------------------------------------------------------------
# GET BY ID
# -----------------------------------------------------------------------


class TestGetHedge:
    def test_get_by_id(self, client, session):
        cp_id = _create_counterparty(session)
        r = client.post(ENDPOINT, json=_make_hedge_payload(cp_id))
        hedge_id = r.json()["id"]
        r2 = client.get(f"{ENDPOINT}/{hedge_id}")
        assert r2.status_code == 200
        assert r2.json()["id"] == hedge_id

    def test_get_not_found(self, client):
        r = client.get(f"{ENDPOINT}/{uuid.uuid4()}")
        assert r.status_code == 404


# -----------------------------------------------------------------------
# UPDATE
# -----------------------------------------------------------------------


class TestUpdateHedge:
    def test_patch_hedge(self, client, session):
        cp_id = _create_counterparty(session)
        r = client.post(ENDPOINT, json=_make_hedge_payload(cp_id))
        hedge_id = r.json()["id"]
        r2 = client.patch(
            f"{ENDPOINT}/{hedge_id}", json={"notes": "Updated note", "tons": 120.0}
        )
        assert r2.status_code == 200
        assert r2.json()["notes"] == "Updated note"
        assert r2.json()["tons"] == 120.0

    def test_patch_not_found(self, client):
        r = client.patch(f"{ENDPOINT}/{uuid.uuid4()}", json={"notes": "x"})
        assert r.status_code == 404


# -----------------------------------------------------------------------
# STATUS TRANSITIONS
# -----------------------------------------------------------------------


class TestStatusTransitions:
    def test_valid_transition_active_to_settled(self, client, session):
        cp_id = _create_counterparty(session)
        r = client.post(ENDPOINT, json=_make_hedge_payload(cp_id))
        hedge_id = r.json()["id"]
        r2 = client.patch(f"{ENDPOINT}/{hedge_id}/status", json={"status": "settled"})
        assert r2.status_code == 200
        assert r2.json()["status"] == "settled"

    def test_valid_transition_active_to_partially_settled(self, client, session):
        cp_id = _create_counterparty(session)
        r = client.post(ENDPOINT, json=_make_hedge_payload(cp_id))
        hedge_id = r.json()["id"]
        r2 = client.patch(
            f"{ENDPOINT}/{hedge_id}/status", json={"status": "partially_settled"}
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "partially_settled"

    def test_invalid_transition_settled_to_active(self, client, session):
        cp_id = _create_counterparty(session)
        r = client.post(ENDPOINT, json=_make_hedge_payload(cp_id))
        hedge_id = r.json()["id"]
        # First settle it
        client.patch(f"{ENDPOINT}/{hedge_id}/status", json={"status": "settled"})
        # Then try to reactivate — should fail
        r2 = client.patch(f"{ENDPOINT}/{hedge_id}/status", json={"status": "active"})
        assert r2.status_code == 409

    def test_invalid_transition_cancelled_to_settled(self, client, session):
        cp_id = _create_counterparty(session)
        r = client.post(ENDPOINT, json=_make_hedge_payload(cp_id))
        hedge_id = r.json()["id"]
        client.patch(f"{ENDPOINT}/{hedge_id}/status", json={"status": "cancelled"})
        r2 = client.patch(f"{ENDPOINT}/{hedge_id}/status", json={"status": "settled"})
        assert r2.status_code == 409

    def test_transition_partially_settled_to_settled(self, client, session):
        cp_id = _create_counterparty(session)
        r = client.post(ENDPOINT, json=_make_hedge_payload(cp_id))
        hedge_id = r.json()["id"]
        client.patch(
            f"{ENDPOINT}/{hedge_id}/status", json={"status": "partially_settled"}
        )
        r2 = client.patch(f"{ENDPOINT}/{hedge_id}/status", json={"status": "settled"})
        assert r2.status_code == 200
        assert r2.json()["status"] == "settled"


# -----------------------------------------------------------------------
# DELETE (soft delete + exposure release)
# -----------------------------------------------------------------------


class TestDeleteHedge:
    def test_delete_soft_deletes(self, client, session):
        cp_id = _create_counterparty(session)
        r = client.post(ENDPOINT, json=_make_hedge_payload(cp_id))
        hedge_id = r.json()["id"]
        r2 = client.delete(f"{ENDPOINT}/{hedge_id}")
        assert r2.status_code == 200
        assert r2.json()["status"] == "cancelled"
        # Should not appear in list
        r3 = client.get(ENDPOINT)
        assert all(h["id"] != hedge_id for h in r3.json()["items"])

    def test_delete_releases_exposure_tons(self, client, session):
        cp_id = _create_counterparty(session)
        exp_id = _create_exposure(session, "long", 100.0)
        payload = _make_hedge_payload(cp_id, exposure_id=str(exp_id), tons=60.0)
        r = client.post(ENDPOINT, json=payload)
        hedge_id = r.json()["id"]
        # Before delete: open_tons should be 40
        exp = session.query(Exposure).filter(Exposure.id == exp_id).first()
        assert exp.open_tons == pytest.approx(40.0)

        # Delete hedge — should release 60 tons back
        client.delete(f"{ENDPOINT}/{hedge_id}")
        session.expire_all()
        exp = session.query(Exposure).filter(Exposure.id == exp_id).first()
        assert exp.open_tons == pytest.approx(100.0)
        assert exp.status == ExposureStatus.open

    def test_delete_not_found(self, client):
        r = client.delete(f"{ENDPOINT}/{uuid.uuid4()}")
        assert r.status_code == 404


# -----------------------------------------------------------------------
# FROM RFQ
# -----------------------------------------------------------------------


class TestFromRFQ:
    def test_create_from_rfq_awarded(self, client, session):
        rfq_id = _create_rfq(session, RFQState.awarded)
        r = client.post(f"{ENDPOINT}/from-rfq/{rfq_id}")
        assert r.status_code == 201
        body = r.json()
        assert body["commodity"] == "ALUMINUM"
        assert body["source_type"] == "rfq_award"
        assert body["status"] == "active"

    def test_create_from_rfq_not_awarded(self, client, session):
        rfq_id = _create_rfq(session, RFQState.created)
        r = client.post(f"{ENDPOINT}/from-rfq/{rfq_id}")
        assert r.status_code == 409

    def test_create_from_rfq_not_found(self, client):
        r = client.post(f"{ENDPOINT}/from-rfq/{uuid.uuid4()}")
        assert r.status_code == 404
