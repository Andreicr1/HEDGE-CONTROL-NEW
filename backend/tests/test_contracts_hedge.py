def _create_hedge_contract(client, quantity_mt: float, legs: list[dict], commodity: str = "LME_AL"):
    response = client.post(
        "/contracts/hedge",
        json={"commodity": commodity, "quantity_mt": quantity_mt, "legs": legs},
    )
    return response


def test_contracts_with_not_two_legs_are_rejected(client) -> None:
    response = _create_hedge_contract(
        client,
        quantity_mt=10.0,
        legs=[{"side": "buy", "price_type": "fixed"}],
    )
    assert response.status_code == 422

    response = _create_hedge_contract(
        client,
        quantity_mt=10.0,
        legs=[
            {"side": "buy", "price_type": "fixed"},
            {"side": "sell", "price_type": "variable"},
            {"side": "buy", "price_type": "variable"},
        ],
    )
    assert response.status_code == 422


def test_contracts_without_exactly_one_fixed_leg_are_rejected(client) -> None:
    response = _create_hedge_contract(
        client,
        quantity_mt=10.0,
        legs=[
            {"side": "buy", "price_type": "variable"},
            {"side": "sell", "price_type": "variable"},
        ],
    )
    assert response.status_code == 422

    response = _create_hedge_contract(
        client,
        quantity_mt=10.0,
        legs=[
            {"side": "buy", "price_type": "fixed"},
            {"side": "sell", "price_type": "fixed"},
        ],
    )
    assert response.status_code == 422


def test_quantity_must_be_positive(client) -> None:
    response = _create_hedge_contract(
        client,
        quantity_mt=0.0,
        legs=[
            {"side": "buy", "price_type": "fixed"},
            {"side": "sell", "price_type": "variable"},
        ],
    )
    assert response.status_code == 422


def test_fixed_buy_classifies_long(client) -> None:
    response = _create_hedge_contract(
        client,
        quantity_mt=12.0,
        legs=[
            {"side": "buy", "price_type": "fixed"},
            {"side": "sell", "price_type": "variable"},
        ],
    )
    assert response.status_code == 201
    data = response.json()
    assert data["classification"] == "long"
    assert data["fixed_leg_side"] == "buy"


def test_fixed_sell_classifies_short(client) -> None:
    response = _create_hedge_contract(
        client,
        quantity_mt=12.0,
        legs=[
            {"side": "sell", "price_type": "fixed"},
            {"side": "buy", "price_type": "variable"},
        ],
    )
    assert response.status_code == 201
    data = response.json()
    assert data["classification"] == "short"
    assert data["fixed_leg_side"] == "sell"


def test_leg_insert_order_does_not_change_classification(client) -> None:
    first = _create_hedge_contract(
        client,
        quantity_mt=8.0,
        legs=[
            {"side": "buy", "price_type": "fixed"},
            {"side": "sell", "price_type": "variable"},
        ],
    ).json()

    second = _create_hedge_contract(
        client,
        quantity_mt=8.0,
        legs=[
            {"side": "sell", "price_type": "variable"},
            {"side": "buy", "price_type": "fixed"},
        ],
    ).json()

    assert first["classification"] == second["classification"]
    assert first["fixed_leg_side"] == second["fixed_leg_side"]


def test_contract_response_has_no_exposure_fields(client) -> None:
    response = _create_hedge_contract(
        client,
        quantity_mt=5.0,
        legs=[
            {"side": "buy", "price_type": "fixed"},
            {"side": "sell", "price_type": "variable"},
        ],
    )
    assert response.status_code == 201
    data = response.json()
    expected_keys = {
        "id",
        "commodity",
        "quantity_mt",
        "fixed_leg_side",
        "variable_leg_side",
        "classification",
        "created_at",
    }
    assert expected_keys.issubset(set(data.keys()))
    assert not any(key.startswith("exposure") for key in data.keys())
