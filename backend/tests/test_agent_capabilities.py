from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from app.services import westmetall_cash_settlement


class _FakeResponse:
    def __init__(self, html: bytes) -> None:
        self.content = html
        self.status_code = 200

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("http error")


def _fake_get_factory(html: bytes):
    def _fake_get(url: str, timeout: float):
        _ = url, timeout
        return _FakeResponse(html)

    return _fake_get


def _create_counterparty(
    client,
    name: str = "Counterparty 1",
    phone: str = "+5511999990001",
) -> str:
    response = client.post(
        "/counterparties",
        json={
            "type": "broker",
            "name": name,
            "country": "BRA",
            "whatsapp_phone": phone,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_rfq(client, counterparty_id: str) -> dict:
    response = client.post(
        "/agent/execute",
        json={
            "capability": "rfq.create",
            "input": {
                "intent": "GLOBAL_POSITION",
                "commodity": "LME_AL",
                "quantity_mt": 5.0,
                "delivery_window_start": "2026-03-01",
                "delivery_window_end": "2026-03-31",
                "direction": "BUY",
                "order_id": None,
                "invitations": [{"counterparty_id": counterparty_id}],
            },
        },
    )
    assert response.status_code == 200
    return response.json()


def test_list_capabilities_includes_rfq_and_thin_domains(client) -> None:
    response = client.get("/agent/capabilities")

    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert "rfq.create" in names
    assert "rfq.process_inbound_message" in names
    assert "orders.list" in names
    assert "contracts.list" in names
    assert "exposures.net" in names
    assert "audit.events.list" in names
    assert "market_data.cash_settlement.list" in names


def test_rfq_context_and_execution_emit_agent_activity(client) -> None:
    counterparty_id = _create_counterparty(client)
    created = _create_rfq(client, counterparty_id)
    rfq_id = created["result"]["id"]

    context_response = client.get(f"/agent/capabilities/rfq.get/context?entity_id={rfq_id}")
    assert context_response.status_code == 200
    context_payload = context_response.json()
    assert context_payload["context"]["rfq"]["id"] == rfq_id
    assert context_payload["latest_activity"]["capability_name"] == "rfq.create"

    rfq_response = client.get(f"/rfqs/{rfq_id}")
    assert rfq_response.status_code == 200
    assert rfq_response.json()["latest_agent_activity"]["capability_name"] == "rfq.create"


def test_rfq_add_quote_updates_rfq_visibility_state(client) -> None:
    counterparty_id = _create_counterparty(client)
    created = _create_rfq(client, counterparty_id)
    rfq_id = created["result"]["id"]

    response = client.post(
        "/agent/execute",
        json={
            "capability": "rfq.add_quote",
            "context_entity_id": rfq_id,
            "input": {
                "rfq_id": rfq_id,
                "counterparty_id": "CP-01",
                "fixed_price_value": 2500.0,
                "fixed_price_unit": "USD/MT",
                "float_pricing_convention": "avg",
                "received_at": datetime(2026, 3, 1, tzinfo=UTC).isoformat(),
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert any(ref["entity_type"] == "rfq_quote" for ref in payload["entity_refs"])

    rfq_response = client.get(f"/rfqs/{rfq_id}")
    assert rfq_response.status_code == 200
    rfq_payload = rfq_response.json()
    assert rfq_payload["state"] == "QUOTED"
    assert rfq_payload["latest_agent_activity"]["capability_name"] == "rfq.add_quote"


def test_inbound_message_returns_review_required_for_question(client) -> None:
    counterparty_id = _create_counterparty(client)
    created = _create_rfq(client, counterparty_id)
    rfq_id = created["result"]["id"]

    with patch("app.services.rfq_orchestrator.LLMAgent.classify_intent") as mock_classify:
        from app.schemas.llm import LLMClassifyResult, MessageIntent

        mock_classify.return_value = LLMClassifyResult(
            intent=MessageIntent.question,
            confidence=0.91,
            raw_reasoning=None,
        )
        response = client.post(
            "/agent/execute",
            json={
                "capability": "rfq.process_inbound_message",
                "input": {
                    "from_phone": "+5511999990001",
                    "text": "What alloy grade?",
                    "sender_name": "Broker Desk",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "review_required"
    assert payload["review_reason"] == "counterparty_question"
    assert any(ref["entity_type"] == "rfq" and ref["entity_id"] == rfq_id for ref in payload["entity_refs"])


def test_thin_domain_capabilities_execute_read_models(client) -> None:
    orders_response = client.post("/orders/sales", json={"price_type": "variable", "quantity_mt": 3.0})
    assert orders_response.status_code == 201

    contracts_response = client.post(
        "/contracts/hedge",
        json={
            "commodity": "LME_AL",
            "quantity_mt": 2.0,
            "legs": [
                {"side": "buy", "price_type": "fixed"},
                {"side": "sell", "price_type": "variable"},
            ],
        },
    )
    assert contracts_response.status_code == 201

    orders_tool = client.post("/agent/execute", json={"capability": "orders.list", "input": {}})
    contracts_tool = client.post("/agent/execute", json={"capability": "contracts.list", "input": {}})
    exposures_tool = client.post("/agent/execute", json={"capability": "exposures.net", "input": {}})

    assert orders_tool.status_code == 200
    assert contracts_tool.status_code == 200
    assert exposures_tool.status_code == 200
    assert orders_tool.json()["status"] == "completed"
    assert contracts_tool.json()["status"] == "completed"
    assert exposures_tool.json()["status"] == "completed"


def test_audit_and_market_data_thin_capabilities_execute_read_models(
    client, monkeypatch
) -> None:
    order_response = client.post(
        "/orders/sales",
        json={"price_type": "variable", "quantity_mt": 3.0},
    )
    assert order_response.status_code == 201

    html = b"""
    <html><body>
      <table>
        <tr><th>Date</th><th>Cash Settlement</th></tr>
        <tr><td>30.01.2026</td><td>2,567.50</td></tr>
      </table>
    </body></html>
    """
    monkeypatch.setattr(
        westmetall_cash_settlement.httpx,
        "get",
        _fake_get_factory(html),
    )
    ingest_response = client.post(
        "/market-data/westmetall/aluminum/cash-settlement/ingest",
        json={"settlement_date": "2026-01-30"},
    )
    assert ingest_response.status_code == 200

    audit_tool = client.post(
        "/agent/execute",
        json={"capability": "audit.events.list", "input": {"entity_type": "order"}},
    )
    market_data_tool = client.post(
        "/agent/execute",
        json={
            "capability": "market_data.cash_settlement.list",
            "input": {"symbol": "LME_ALU_CASH_SETTLEMENT_DAILY"},
        },
    )

    assert audit_tool.status_code == 200
    assert market_data_tool.status_code == 200
    assert audit_tool.json()["status"] == "completed"
    assert market_data_tool.json()["status"] == "completed"
    assert len(audit_tool.json()["result"]["events"]) >= 1
    assert len(market_data_tool.json()["result"]["items"]) == 1
