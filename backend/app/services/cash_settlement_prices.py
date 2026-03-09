from __future__ import annotations

import calendar
import uuid as _uuid
from collections import defaultdict
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.models.market_data import CashSettlementPrice
from app.schemas.market_data import CashSettlementPriceRead
from app.services.westmetall_cash_settlement import (
    SOURCE_WESTMETALL,
    SYMBOL_DAILY,
    WESTMETALL_DAILY_URL,
    WestmetallFetchEvidence,
    fetch_westmetall_html,
    parse_westmetall_daily_rows,
)

SYMBOL_MONTHLY_AVG = "LME_ALU_MONTHLY_AVG"
_NS_MONTHLY = _uuid.UUID("b3a1c2d4-e5f6-4890-abcd-ef1234567890")


def compute_monthly_averages(
    db: Session,
    start_date: date | None,
    end_date: date | None,
    limit: int,
) -> list[CashSettlementPriceRead]:
    """Compute monthly-average prices from daily cash-settlement rows."""
    query = db.query(CashSettlementPrice).filter(
        CashSettlementPrice.symbol == SYMBOL_DAILY,
    )
    if start_date:
        query = query.filter(CashSettlementPrice.settlement_date >= start_date)
    if end_date:
        query = query.filter(CashSettlementPrice.settlement_date <= end_date)
    rows = query.order_by(CashSettlementPrice.settlement_date.asc()).all()

    monthly: dict[tuple[int, int], list[float]] = defaultdict(list)
    for row in rows:
        monthly[(row.settlement_date.year, row.settlement_date.month)].append(
            row.price_usd
        )

    now = datetime.now(UTC)
    results: list[CashSettlementPriceRead] = []
    for (year, month), prices in sorted(monthly.items(), reverse=True):
        last_day = calendar.monthrange(year, month)[1]
        avg_price = sum(prices) / len(prices)
        month_id = _uuid.uuid5(_NS_MONTHLY, f"{year}-{month:02d}")
        results.append(
            CashSettlementPriceRead(
                id=month_id,
                source="computed",
                symbol=SYMBOL_MONTHLY_AVG,
                settlement_date=date(year, month, last_day),
                price_usd=round(avg_price, 2),
                source_url="computed_from_daily",
                html_sha256="n/a",
                fetched_at=now,
                created_at=now,
            )
        )
    return results[:limit]


def list_cash_settlement_prices(
    db: Session,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    symbol: str | None = None,
    limit: int = 500,
) -> list[CashSettlementPriceRead]:
    if symbol and symbol.upper() == SYMBOL_MONTHLY_AVG:
        return compute_monthly_averages(db, start_date, end_date, limit)

    query = db.query(CashSettlementPrice)
    if start_date:
        query = query.filter(CashSettlementPrice.settlement_date >= start_date)
    if end_date:
        query = query.filter(CashSettlementPrice.settlement_date <= end_date)
    if symbol:
        query = query.filter(CashSettlementPrice.symbol.ilike(f"%{symbol}%"))
    rows = query.order_by(CashSettlementPrice.settlement_date.desc()).limit(limit).all()
    return [CashSettlementPriceRead.model_validate(row) for row in rows]


def ingest_westmetall_cash_settlement_daily_for_date(
    db: Session,
    settlement_date: date,
) -> tuple[int, int, WestmetallFetchEvidence]:
    html, evidence = fetch_westmetall_html(WESTMETALL_DAILY_URL)
    rows = parse_westmetall_daily_rows(html)
    row = next((r for r in rows if r.settlement_date == settlement_date), None)
    if row is None:
        return 0, 0, evidence

    existing = (
        db.query(CashSettlementPrice)
        .filter(
            CashSettlementPrice.source == SOURCE_WESTMETALL,
            CashSettlementPrice.symbol == SYMBOL_DAILY,
            CashSettlementPrice.settlement_date == settlement_date,
        )
        .first()
    )
    if existing is not None:
        return 0, 1, evidence

    price = CashSettlementPrice(
        source=SOURCE_WESTMETALL,
        symbol=SYMBOL_DAILY,
        settlement_date=settlement_date,
        price_usd=row.price_usd,
        source_url=evidence.source_url,
        html_sha256=evidence.html_sha256,
        fetched_at=evidence.fetched_at,
    )
    db.add(price)
    db.commit()
    return 1, 0, evidence


def ingest_westmetall_cash_settlement_bulk(
    db: Session,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[int, int, WestmetallFetchEvidence]:
    """Fetch Westmetall and ingest all available daily rows.

    Optionally restrict to ``[start_date, end_date]``.
    Returns ``(ingested_count, skipped_count, evidence)``.
    """
    html, evidence = fetch_westmetall_html(WESTMETALL_DAILY_URL)
    rows = parse_westmetall_daily_rows(html)

    if start_date:
        rows = [r for r in rows if r.settlement_date >= start_date]
    if end_date:
        rows = [r for r in rows if r.settlement_date <= end_date]

    if not rows:
        return 0, 0, evidence

    # Fetch existing dates in one query to avoid N+1
    existing_dates = set(
        d
        for (d,) in db.query(CashSettlementPrice.settlement_date)
        .filter(
            CashSettlementPrice.source == SOURCE_WESTMETALL,
            CashSettlementPrice.symbol == SYMBOL_DAILY,
            CashSettlementPrice.settlement_date.in_(
                [r.settlement_date for r in rows]
            ),
        )
        .all()
    )

    ingested = 0
    skipped = 0
    for row in rows:
        if row.settlement_date in existing_dates:
            skipped += 1
            continue
        db.add(
            CashSettlementPrice(
                source=SOURCE_WESTMETALL,
                symbol=SYMBOL_DAILY,
                settlement_date=row.settlement_date,
                price_usd=row.price_usd,
                source_url=evidence.source_url,
                html_sha256=evidence.html_sha256,
                fetched_at=evidence.fetched_at,
            )
        )
        ingested += 1

    if ingested:
        db.commit()

    return ingested, skipped, evidence

