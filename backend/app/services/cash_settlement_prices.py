from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.market_data import CashSettlementPrice
from app.services.westmetall_cash_settlement import (
    SOURCE_WESTMETALL,
    SYMBOL_DAILY,
    WESTMETALL_DAILY_URL,
    WestmetallFetchEvidence,
    fetch_westmetall_html,
    parse_westmetall_daily_rows,
)


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
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
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

