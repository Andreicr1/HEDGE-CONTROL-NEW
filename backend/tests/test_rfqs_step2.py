from datetime import datetime, timezone


def _create_trade_rfq(client, direction: str) -> str:
    response = client.post(
        "/rfqs",
        json={
            "intent": "GLOBAL_POSITION",
            "commodity": "LME_AL",
            "quantity_mt": 5.0,
            "delivery_window_start": "2026-03-01",
            "delivery_window_end": "2026-03-31",
            "direction": direction,
            "order_id": None,
            "invitations": [
                {
                    "recipient_id": "CP_INV",
                    "recipient_name": "Counterparty",
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
    assert response.status_code == 201
    assert response.json()["state"] == "SENT"
    return response.json()["id"]


def _create_spread_rfq(client, buy_trade_id: str, sell_trade_id: str) -> str:
    response = client.post(
        "/rfqs",
        json={
            "intent": "SPREAD",
            "commodity": "LME_AL",
            "quantity_mt": 5.0,
            "delivery_window_start": "2026-03-01",
            "delivery_window_end": "2026-03-31",
            "direction": "BUY",
            "order_id": None,
            "buy_trade_id": buy_trade_id,
            "sell_trade_id": sell_trade_id,
            "invitations": [],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_quote(client, rfq_id: str, payload: dict):
    return client.post(f"/rfqs/{rfq_id}/quotes", json=payload)


def _get_rfq(client, rfq_id: str) -> dict:
    response = client.get(f"/rfqs/{rfq_id}")
    assert response.status_code == 200
    return response.json()


def _get_ranking(client, rfq_id: str):
    return client.get(f"/rfqs/{rfq_id}/ranking")


def test_incomplete_quote_is_rejected(client) -> None:
    trade_rfq_id = _create_trade_rfq(client, "BUY")
    response = _create_quote(
        client,
        trade_rfq_id,
        {
            "rfq_id": trade_rfq_id,
            "counterparty_id": "CP1",
            "fixed_price_value": 100.0,
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 422


def test_first_quote_transitions_rfq_to_quoted(client) -> None:
    trade_rfq_id = _create_trade_rfq(client, "BUY")
    assert _get_rfq(client, trade_rfq_id)["state"] == "SENT"

    response = _create_quote(
        client,
        trade_rfq_id,
        {
            "rfq_id": trade_rfq_id,
            "counterparty_id": "CP1",
            "fixed_price_value": 100.0,
            "fixed_price_unit": "USD/MT",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 201
    assert _get_rfq(client, trade_rfq_id)["state"] == "QUOTED"


def test_spread_ranking_descending_and_ignores_missing_counterparty(client) -> None:
    buy_trade_id = _create_trade_rfq(client, "BUY")
    sell_trade_id = _create_trade_rfq(client, "SELL")
    spread_rfq_id = _create_spread_rfq(client, buy_trade_id, sell_trade_id)

    # CP1 spread = 110 - 100 = 10
    _create_quote(
        client,
        buy_trade_id,
        {
            "rfq_id": buy_trade_id,
            "counterparty_id": "CP1",
            "fixed_price_value": 100.0,
            "fixed_price_unit": "USD/MT",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )
    _create_quote(
        client,
        sell_trade_id,
        {
            "rfq_id": sell_trade_id,
            "counterparty_id": "CP1",
            "fixed_price_value": 110.0,
            "fixed_price_unit": "usd-mt",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )

    # CP2 spread = 115 - 102 = 13
    _create_quote(
        client,
        buy_trade_id,
        {
            "rfq_id": buy_trade_id,
            "counterparty_id": "CP2",
            "fixed_price_value": 102.0,
            "fixed_price_unit": "USD/MT",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )
    _create_quote(
        client,
        sell_trade_id,
        {
            "rfq_id": sell_trade_id,
            "counterparty_id": "CP2",
            "fixed_price_value": 115.0,
            "fixed_price_unit": "USDMT",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )

    # CP3 only quotes one side -> ignored
    _create_quote(
        client,
        sell_trade_id,
        {
            "rfq_id": sell_trade_id,
            "counterparty_id": "CP3",
            "fixed_price_value": 150.0,
            "fixed_price_unit": "USD/MT",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )

    ranking = _get_ranking(client, spread_rfq_id)
    assert ranking.status_code == 200
    payload = ranking.json()
    assert payload["status"] == "SUCCESS"
    assert payload["failure_code"] is None

    data = payload["ranking"]
    assert data[0]["counterparty_id"] == "CP2"
    assert data[0]["spread_value"] == 13.0
    assert data[1]["counterparty_id"] == "CP1"
    assert data[1]["spread_value"] == 10.0


def test_spread_ranking_zero_eligible_quotes_returns_failure_payload(client) -> None:
    buy_trade_id = _create_trade_rfq(client, "BUY")
    sell_trade_id = _create_trade_rfq(client, "SELL")
    spread_rfq_id = _create_spread_rfq(client, buy_trade_id, sell_trade_id)

    _create_quote(
        client,
        buy_trade_id,
        {
            "rfq_id": buy_trade_id,
            "counterparty_id": "CP1",
            "fixed_price_value": 100.0,
            "fixed_price_unit": "USD/MT",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )

    ranking = _get_ranking(client, spread_rfq_id)
    assert ranking.status_code == 200
    payload = ranking.json()
    assert payload["status"] == "FAILURE"
    assert payload["failure_code"] == "NO_ELIGIBLE_QUOTES"
    assert payload["ranking"] == []


def test_spread_ranking_non_canonical_unit_fails(client) -> None:
    buy_trade_id = _create_trade_rfq(client, "BUY")
    sell_trade_id = _create_trade_rfq(client, "SELL")
    spread_rfq_id = _create_spread_rfq(client, buy_trade_id, sell_trade_id)

    _create_quote(
        client,
        buy_trade_id,
        {
            "rfq_id": buy_trade_id,
            "counterparty_id": "CP1",
            "fixed_price_value": 100.0,
            "fixed_price_unit": "USD/KG",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )
    _create_quote(
        client,
        sell_trade_id,
        {
            "rfq_id": sell_trade_id,
            "counterparty_id": "CP1",
            "fixed_price_value": 110.0,
            "fixed_price_unit": "USD/MT",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )

    ranking = _get_ranking(client, spread_rfq_id)
    assert ranking.status_code == 200
    payload = ranking.json()
    assert payload["status"] == "FAILURE"
    assert payload["failure_code"] == "NON_COMPARABLE"


def test_spread_ranking_tie_fails(client) -> None:
    buy_trade_id = _create_trade_rfq(client, "BUY")
    sell_trade_id = _create_trade_rfq(client, "SELL")
    spread_rfq_id = _create_spread_rfq(client, buy_trade_id, sell_trade_id)

    # CP1 spread = 10
    _create_quote(
        client,
        buy_trade_id,
        {
            "rfq_id": buy_trade_id,
            "counterparty_id": "CP1",
            "fixed_price_value": 100.0,
            "fixed_price_unit": "USD/MT",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )
    _create_quote(
        client,
        sell_trade_id,
        {
            "rfq_id": sell_trade_id,
            "counterparty_id": "CP1",
            "fixed_price_value": 110.0,
            "fixed_price_unit": "USD/MT",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )

    # CP2 spread = 10 (tie)
    _create_quote(
        client,
        buy_trade_id,
        {
            "rfq_id": buy_trade_id,
            "counterparty_id": "CP2",
            "fixed_price_value": 105.0,
            "fixed_price_unit": "USD/MT",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )
    _create_quote(
        client,
        sell_trade_id,
        {
            "rfq_id": sell_trade_id,
            "counterparty_id": "CP2",
            "fixed_price_value": 115.0,
            "fixed_price_unit": "USD/MT",
            "float_pricing_convention": "avg",
            "received_at": datetime(2026, 2, 1, tzinfo=timezone.utc).isoformat(),
        },
    )

    ranking = _get_ranking(client, spread_rfq_id)
    assert ranking.status_code == 200
    payload = ranking.json()
    assert payload["status"] == "FAILURE"
    assert payload["failure_code"] == "TIE"

