"""Tests for soft-delete (archived) behavior on orders, contracts, and RFQs."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient


def _create_sales_order(client: TestClient) -> dict:
    resp = client.post(
        "/orders/sales",
        json={"price_type": "fixed", "quantity_mt": 100},
    )
    assert resp.status_code == 201
    return resp.json()


def _create_hedge_contract(client: TestClient) -> dict:
    resp = client.post(
        "/contracts/hedge",
        json={
            "commodity": "Zinc",
            "quantity_mt": 50,
            "legs": [
                {"side": "buy", "price_type": "fixed"},
                {"side": "sell", "price_type": "variable"},
            ],
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _create_rfq(client: TestClient, order_id: str) -> dict:
    resp = client.post(
        "/rfqs",
        json={
            "intent": "COMMERCIAL_HEDGE",
            "commodity": "LME_AL",
            "quantity_mt": 5.0,
            "delivery_window_start": "2026-03-01",
            "delivery_window_end": "2026-03-31",
            "direction": "SELL",
            "order_id": order_id,
            "invitations": [
                {
                    "recipient_id": "CP1",
                    "recipient_name": "Counterparty 1",
                    "channel": "email",
                    "message_body": "RFQ request",
                    "provider_message_id": "msg-1",
                    "send_status": "queued",
                    "sent_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
                    "idempotency_key": "idem-1",
                }
            ],
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ── Order soft-delete ────────────────────────────────────────────────


class TestOrderSoftDelete:
    def test_archive_order_sets_deleted_at(self, client: TestClient):
        order = _create_sales_order(client)
        resp = client.patch(f"/orders/{order['id']}/archive")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted_at"] is not None

    def test_archived_order_excluded_from_list(self, client: TestClient):
        order = _create_sales_order(client)
        client.patch(f"/orders/{order['id']}/archive")
        resp = client.get("/orders")
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json()["items"]]
        assert order["id"] not in ids

    def test_include_deleted_shows_archived_order(self, client: TestClient):
        order = _create_sales_order(client)
        client.patch(f"/orders/{order['id']}/archive")
        resp = client.get("/orders?include_deleted=true")
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json()["items"]]
        assert order["id"] in ids

    def test_archive_already_archived_returns_409(self, client: TestClient):
        order = _create_sales_order(client)
        client.patch(f"/orders/{order['id']}/archive")
        resp = client.patch(f"/orders/{order['id']}/archive")
        assert resp.status_code == 409

    def test_archive_nonexistent_order_returns_404(self, client: TestClient):
        resp = client.patch("/orders/00000000-0000-0000-0000-000000000000/archive")
        assert resp.status_code == 404


# ── HedgeContract soft-delete ────────────────────────────────────────


class TestContractSoftDelete:
    def test_archive_contract_sets_deleted_at(self, client: TestClient):
        contract = _create_hedge_contract(client)
        resp = client.patch(f"/contracts/hedge/{contract['id']}/archive")
        assert resp.status_code == 200
        assert resp.json()["deleted_at"] is not None

    def test_archived_contract_excluded_from_list(self, client: TestClient):
        contract = _create_hedge_contract(client)
        client.patch(f"/contracts/hedge/{contract['id']}/archive")
        resp = client.get("/contracts/hedge")
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()["items"]]
        assert contract["id"] not in ids

    def test_include_deleted_shows_archived_contract(self, client: TestClient):
        contract = _create_hedge_contract(client)
        client.patch(f"/contracts/hedge/{contract['id']}/archive")
        resp = client.get("/contracts/hedge?include_deleted=true")
        assert resp.status_code == 200
        ids = [c["id"] for c in resp.json()["items"]]
        assert contract["id"] in ids

    def test_archive_already_archived_returns_409(self, client: TestClient):
        contract = _create_hedge_contract(client)
        client.patch(f"/contracts/hedge/{contract['id']}/archive")
        resp = client.patch(f"/contracts/hedge/{contract['id']}/archive")
        assert resp.status_code == 409

    def test_archive_nonexistent_contract_returns_404(self, client: TestClient):
        resp = client.patch(
            "/contracts/hedge/00000000-0000-0000-0000-000000000000/archive"
        )
        assert resp.status_code == 404


# ── RFQ soft-delete ──────────────────────────────────────────────────


class TestRFQSoftDelete:
    @staticmethod
    def _create_variable_order(client: TestClient) -> dict:
        resp = client.post(
            "/orders/sales",
            json={"price_type": "variable", "quantity_mt": 100},
        )
        assert resp.status_code == 201
        return resp.json()

    def test_archive_rfq_sets_deleted_at(self, client: TestClient):
        order = self._create_variable_order(client)
        rfq = _create_rfq(client, order["id"])
        resp = client.patch(f"/rfqs/{rfq['id']}/archive")
        assert resp.status_code == 200
        assert resp.json()["deleted_at"] is not None

    def test_archived_rfq_excluded_from_list(self, client: TestClient):
        order = self._create_variable_order(client)
        rfq = _create_rfq(client, order["id"])
        client.patch(f"/rfqs/{rfq['id']}/archive")
        resp = client.get("/rfqs")
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()["items"]]
        assert rfq["id"] not in ids

    def test_include_deleted_shows_archived_rfq(self, client: TestClient):
        order = self._create_variable_order(client)
        rfq = _create_rfq(client, order["id"])
        client.patch(f"/rfqs/{rfq['id']}/archive")
        resp = client.get("/rfqs?include_deleted=true")
        assert resp.status_code == 200
        ids = [r["id"] for r in resp.json()["items"]]
        assert rfq["id"] in ids

    def test_archive_already_archived_returns_409(self, client: TestClient):
        order = self._create_variable_order(client)
        rfq = _create_rfq(client, order["id"])
        client.patch(f"/rfqs/{rfq['id']}/archive")
        resp = client.patch(f"/rfqs/{rfq['id']}/archive")
        assert resp.status_code == 409

    def test_archive_nonexistent_rfq_returns_404(self, client: TestClient):
        resp = client.patch("/rfqs/00000000-0000-0000-0000-000000000000/archive")
        assert resp.status_code == 404
