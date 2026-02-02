from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from app.core.database import SessionLocal
from app.models.contracts import HedgeClassification, HedgeContract, HedgeContractStatus, HedgeLegSide
from app.models.market_data import CashSettlementPrice
from app.services.cashflow_ledger_service import ingest_hedge_contract_settlement
from app.schemas.cashflow import HedgeContractSettlementCreate
from app.services.pl_calculation_service import compute_pl


def _insert_price(symbol: str, settlement_date: date, price_usd: float) -> None:
    with SessionLocal() as session:
        session.add(
            CashSettlementPrice(
                source="westmetall",
                symbol=symbol,
                settlement_date=settlement_date,
                price_usd=price_usd,
                source_url="https://example.test/source",
                html_sha256="0" * 64,
                fetched_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            )
        )
        session.commit()


def _insert_contract(quantity_mt: float, entry_price: float, status: HedgeContractStatus) -> HedgeContract:
    with SessionLocal() as session:
        contract = HedgeContract(
            commodity="LME_AL",
            quantity_mt=quantity_mt,
            fixed_leg_side=HedgeLegSide.buy,
            variable_leg_side=HedgeLegSide.sell,
            classification=HedgeClassification.long,
            fixed_price_value=entry_price,
            fixed_price_unit="USD/MT",
            float_pricing_convention="avg",
            status=status,
        )
        session.add(contract)
        session.commit()
        session.refresh(contract)
        return contract


def _settlement_payload(source_event_id: str) -> HedgeContractSettlementCreate:
    return HedgeContractSettlementCreate(
        source_event_id=source_event_id,
        cashflow_date=date(2026, 1, 15),
        legs=[
            {"leg_id": "FIXED", "direction": "OUT", "amount": Decimal("100.00")},
            {"leg_id": "FLOAT", "direction": "IN", "amount": Decimal("110.00")},
        ],
    )


def test_realized_pl_from_ledger() -> None:
    symbol = "LME_ALU_CASH_SETTLEMENT_DAILY"
    _insert_price(symbol=symbol, settlement_date=date(2026, 1, 14), price_usd=100.0)
    _insert_price(symbol=symbol, settlement_date=date(2026, 1, 31), price_usd=110.0)
    contract = _insert_contract(quantity_mt=5.0, entry_price=100.0, status=HedgeContractStatus.active)
    payload = _settlement_payload(str(uuid4()))

    with SessionLocal() as session:
        ingest_hedge_contract_settlement(session, contract.id, payload)

    with SessionLocal() as session:
        result = compute_pl(
            session,
            entity_type="hedge_contract",
            entity_id=contract.id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        assert result.realized_pl == Decimal("10.00")


def test_realized_pl_idempotent_on_reprocess() -> None:
    symbol = "LME_ALU_CASH_SETTLEMENT_DAILY"
    _insert_price(symbol=symbol, settlement_date=date(2026, 1, 14), price_usd=100.0)
    _insert_price(symbol=symbol, settlement_date=date(2026, 1, 31), price_usd=110.0)
    contract = _insert_contract(quantity_mt=5.0, entry_price=100.0, status=HedgeContractStatus.active)
    source_event_id = str(uuid4())
    payload = _settlement_payload(source_event_id)

    with SessionLocal() as session:
        ingest_hedge_contract_settlement(session, contract.id, payload)

    with SessionLocal() as session:
        ingest_hedge_contract_settlement(session, contract.id, payload)

    with SessionLocal() as session:
        result = compute_pl(
            session,
            entity_type="hedge_contract",
            entity_id=contract.id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        assert result.realized_pl == Decimal("10.00")


def test_realized_pl_orders_hard_fail() -> None:
    with SessionLocal() as session:
        with pytest.raises(HTTPException) as exc:
            compute_pl(
                session,
                entity_type="order",
                entity_id=uuid4(),
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
            )
        assert exc.value.status_code in {status.HTTP_424_FAILED_DEPENDENCY, status.HTTP_422_UNPROCESSABLE_ENTITY}
        assert "Realized cashflow ledger not implemented for orders" in exc.value.detail
