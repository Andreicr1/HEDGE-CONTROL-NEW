from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from app.core.database import SessionLocal
from app.models.contracts import HedgeClassification, HedgeContract, HedgeContractStatus, HedgeLegSide
from app.models.market_data import CashSettlementPrice
from app.models.pl import PLSnapshot
from app.services.cashflow_ledger_service import ingest_hedge_contract_settlement
from app.schemas.cashflow import HedgeContractSettlementCreate
from app.services.pl_snapshot_service import create_pl_snapshot


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


def test_pl_snapshot_realized_from_ledger_is_idempotent() -> None:
    symbol = "LME_ALU_CASH_SETTLEMENT_DAILY"
    _insert_price(symbol=symbol, settlement_date=date(2026, 1, 14), price_usd=100.0)
    _insert_price(symbol=symbol, settlement_date=date(2026, 1, 31), price_usd=110.0)
    contract = _insert_contract(quantity_mt=5.0, entry_price=100.0, status=HedgeContractStatus.active)
    payload = _settlement_payload(str(uuid4()))

    with SessionLocal() as session:
        ingest_hedge_contract_settlement(session, contract.id, payload)

    with SessionLocal() as session:
        first = create_pl_snapshot(
            session,
            entity_type="hedge_contract",
            entity_id=contract.id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        assert first.realized_pl == Decimal("10.00")

    with SessionLocal() as session:
        second = create_pl_snapshot(
            session,
            entity_type="hedge_contract",
            entity_id=contract.id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
        )
        assert second.id == first.id
        assert second.realized_pl == Decimal("10.00")


def test_pl_snapshot_conflict_on_divergent_ledger() -> None:
    symbol = "LME_ALU_CASH_SETTLEMENT_DAILY"
    _insert_price(symbol=symbol, settlement_date=date(2026, 1, 14), price_usd=100.0)
    _insert_price(symbol=symbol, settlement_date=date(2026, 1, 31), price_usd=110.0)
    contract = _insert_contract(quantity_mt=5.0, entry_price=100.0, status=HedgeContractStatus.active)

    payload_first = _settlement_payload(str(uuid4()))

    with SessionLocal() as session:
        ingest_hedge_contract_settlement(session, contract.id, payload_first)

    with SessionLocal() as session:
        session.add(
            PLSnapshot(
                entity_type="hedge_contract",
                entity_id=contract.id,
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
                realized_pl=Decimal("999.00"),
                unrealized_mtm=Decimal("0"),
            )
        )
        session.commit()

    with SessionLocal() as session:
        with pytest.raises(HTTPException) as exc:
            create_pl_snapshot(
                session,
                entity_type="hedge_contract",
                entity_id=contract.id,
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
            )
        assert exc.value.status_code == status.HTTP_409_CONFLICT

        snapshot = (
            session.query(PLSnapshot)
            .filter(
                PLSnapshot.entity_type == "hedge_contract",
                PLSnapshot.entity_id == contract.id,
                PLSnapshot.period_start == date(2026, 1, 1),
                PLSnapshot.period_end == date(2026, 1, 31),
            )
            .first()
        )
        assert snapshot is not None
        assert snapshot.realized_pl == Decimal("999.00")


def test_pl_snapshot_order_hard_fails() -> None:
    with SessionLocal() as session:
        with pytest.raises(HTTPException) as exc:
            create_pl_snapshot(
                session,
                entity_type="order",
                entity_id=uuid4(),
                period_start=date(2026, 1, 1),
                period_end=date(2026, 1, 31),
            )
        assert exc.value.status_code in {status.HTTP_424_FAILED_DEPENDENCY, status.HTTP_422_UNPROCESSABLE_ENTITY}
        assert "Realized cashflow ledger not implemented for orders" in exc.value.detail