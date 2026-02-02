from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.database import SessionLocal
from app.models.market_data import CashSettlementPrice
from app.services.price_lookup_service import get_cash_settlement_price_d1


def _insert_price(symbol: str, settlement_date: date, price_usd: float, source: str = "westmetall") -> None:
    with SessionLocal() as session:
        session.add(
            CashSettlementPrice(
                source=source,
                symbol=symbol,
                settlement_date=settlement_date,
                price_usd=price_usd,
                source_url="https://example.test/source",
                html_sha256="0" * 64,
                fetched_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            )
        )
        session.commit()


def test_d1_price_exists_returns_decimal() -> None:
    symbol = "LME_ALU_CASH_SETTLEMENT_DAILY"
    _insert_price(symbol=symbol, settlement_date=date(2026, 1, 31), price_usd=2567.50)

    with SessionLocal() as session:
        value = get_cash_settlement_price_d1(session, symbol=symbol, as_of_date=date(2026, 2, 1))
        assert value == Decimal("2567.5")


def test_d1_price_missing_raises_http_424() -> None:
    with SessionLocal() as session:
        with pytest.raises(HTTPException) as exc:
            get_cash_settlement_price_d1(
                session,
                symbol="LME_ALU_CASH_SETTLEMENT_DAILY",
                as_of_date=date(2026, 2, 1),
            )
        assert exc.value.status_code == 424


def test_as_of_date_2026_02_01_uses_calendar_d1_2026_01_31() -> None:
    symbol = "LME_ALU_CASH_SETTLEMENT_DAILY"
    _insert_price(symbol=symbol, settlement_date=date(2026, 1, 31), price_usd=111.0)

    with SessionLocal() as session:
        value = get_cash_settlement_price_d1(session, symbol=symbol, as_of_date=date(2026, 2, 1))
        assert value == Decimal("111.0")


def test_weekend_d1_is_valid_if_price_exists() -> None:
    # as_of_date 2026-02-02 is Monday; D-1 is 2026-02-01 (Sunday)
    symbol = "LME_ALU_CASH_SETTLEMENT_DAILY"
    _insert_price(symbol=symbol, settlement_date=date(2026, 2, 1), price_usd=222.0)

    with SessionLocal() as session:
        value = get_cash_settlement_price_d1(session, symbol=symbol, as_of_date=date(2026, 2, 2))
        assert value == Decimal("222.0")

