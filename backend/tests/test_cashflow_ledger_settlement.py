from datetime import date
from uuid import uuid4

from fastapi import status


def _create_hedge_contract(client) -> str:
    response = client.post(
        "/contracts/hedge",
        json={
            "commodity": "LME_AL",
            "quantity_mt": 12.0,
            "legs": [
                {"side": "buy", "price_type": "fixed"},
                {"side": "sell", "price_type": "variable"},
            ],
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()["id"]


def _settlement_payload(source_event_id: str, amount_fixed: str = "100", amount_float: str = "120") -> dict:
    return {
        "source_event_id": source_event_id,
        "cashflow_date": date(2026, 1, 15).isoformat(),
        "legs": [
            {"leg_id": "FIXED", "direction": "IN", "amount": amount_fixed},
            {"leg_id": "FLOAT", "direction": "OUT", "amount": amount_float},
        ],
    }


def test_settlement_creates_event_and_ledger_entries_and_sets_status(client) -> None:
    contract_id = _create_hedge_contract(client)
    payload = _settlement_payload(str(uuid4()))
    response = client.post(f"/cashflow/contracts/{contract_id}/settle", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["event"]["hedge_contract_id"] == contract_id
    assert data["event"]["cashflow_date"] == payload["cashflow_date"]
    assert len(data["ledger_entries"]) == 2

    contract_response = client.get(f"/contracts/hedge/{contract_id}")
    assert contract_response.status_code == status.HTTP_200_OK
    assert contract_response.json()["status"] == "settled"


def test_settlement_is_idempotent_with_same_payload(client) -> None:
    contract_id = _create_hedge_contract(client)
    source_event_id = str(uuid4())
    payload = _settlement_payload(source_event_id)

    first = client.post(f"/cashflow/contracts/{contract_id}/settle", json=payload)
    assert first.status_code == status.HTTP_201_CREATED

    second = client.post(f"/cashflow/contracts/{contract_id}/settle", json=payload)
    assert second.status_code == status.HTTP_201_CREATED
    assert second.json()["event"]["id"] == source_event_id


def test_settlement_conflicts_on_different_payload(client) -> None:
    contract_id = _create_hedge_contract(client)
    source_event_id = str(uuid4())
    payload = _settlement_payload(source_event_id)

    first = client.post(f"/cashflow/contracts/{contract_id}/settle", json=payload)
    assert first.status_code == status.HTTP_201_CREATED

    updated_payload = _settlement_payload(source_event_id, amount_fixed="150")
    second = client.post(f"/cashflow/contracts/{contract_id}/settle", json=updated_payload)
    assert second.status_code == status.HTTP_409_CONFLICT


def test_settlement_rejected_for_non_active_contract(client) -> None:
    contract_id = _create_hedge_contract(client)
    payload = _settlement_payload(str(uuid4()))
    first = client.post(f"/cashflow/contracts/{contract_id}/settle", json=payload)
    assert first.status_code == status.HTTP_201_CREATED

    second = client.post(f"/cashflow/contracts/{contract_id}/settle", json=_settlement_payload(str(uuid4())))
    assert second.status_code == status.HTTP_409_CONFLICT


def test_currency_must_be_usd(client) -> None:
    contract_id = _create_hedge_contract(client)
    payload = _settlement_payload(str(uuid4()))
    payload["currency"] = "BRL"
    response = client.post(f"/cashflow/contracts/{contract_id}/settle", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_amount_must_be_positive(client) -> None:
    contract_id = _create_hedge_contract(client)
    payload = _settlement_payload(str(uuid4()), amount_fixed="0")
    response = client.post(f"/cashflow/contracts/{contract_id}/settle", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY