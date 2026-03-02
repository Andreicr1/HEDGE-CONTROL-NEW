from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.market_data import CashSettlementPrice

# ── Commodity → Price-symbol mapping ───────────────────────────────────
# Each tradeable commodity is mapped to the symbol that its cash-settlement
# price is published under.  Adding a new commodity is a one-liner here.

COMMODITY_SYMBOL_MAP: dict[str, str] = {
    "LME_AL": "LME_ALU_CASH_SETTLEMENT_DAILY",
    "LME_CU": "LME_CU_CASH_SETTLEMENT_DAILY",
    "LME_ZN": "LME_ZN_CASH_SETTLEMENT_DAILY",
    "LME_NI": "LME_NI_CASH_SETTLEMENT_DAILY",
    "LME_PB": "LME_PB_CASH_SETTLEMENT_DAILY",
    "LME_SN": "LME_SN_CASH_SETTLEMENT_DAILY",
}


def resolve_symbol(commodity: str) -> str:
    """Return the settlement-price symbol for *commodity*.

    Raises 400 when there is no mapping.
    """
    sym = COMMODITY_SYMBOL_MAP.get(commodity)
    if sym is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No price-symbol mapping for commodity '{commodity}'",
        )
    return sym


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
