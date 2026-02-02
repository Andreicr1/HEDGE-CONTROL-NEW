from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.market_data import CashSettlementPrice


def get_cash_settlement_price_d1(db: Session, symbol: str, as_of_date: date) -> Decimal:
    price_date = as_of_date - timedelta(days=1)

    rows = (
        db.query(CashSettlementPrice)
        .filter(
            CashSettlementPrice.symbol == symbol,
            CashSettlementPrice.settlement_date == price_date,
        )
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=f"No cash settlement price for {symbol} on {price_date}",
        )

    if len(rows) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ambiguous cash settlement price for {symbol} on {price_date}",
        )

    return Decimal(str(rows[0].price_usd))

