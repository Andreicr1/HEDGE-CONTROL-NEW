from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies.audit import audit_event
from app.core.auth import require_any_role, require_role
from app.core.database import get_session
from app.core.rate_limit import RATE_LIMIT_SCRAPING, limiter
from app.schemas.market_data import (
    CashSettlementBulkIngestRequest,
    CashSettlementBulkIngestResponse,
    CashSettlementIngestRequest,
    CashSettlementIngestResponse,
    CashSettlementPriceRead,
)
from app.services.cash_settlement_prices import (
    ingest_westmetall_cash_settlement_bulk,
    ingest_westmetall_cash_settlement_daily_for_date,
)
from app.services.cash_settlement_prices import (
    list_cash_settlement_prices as list_cash_settlement_prices_service,
)
from app.services.westmetall_cash_settlement import (
    SOURCE_WESTMETALL,
    SYMBOL_DAILY,
    CircuitOpenError,
    WestmetallLayoutError,
)

router = APIRouter()


@router.get(
    "/aluminum/cash-settlement/prices",
    response_model=list[CashSettlementPriceRead],
    status_code=status.HTTP_200_OK,
)
def list_cash_settlement_prices(
    start_date: date | None = Query(
        None, description="Start of date range (inclusive)"
    ),
    end_date: date | None = Query(None, description="End of date range (inclusive)"),
    symbol: str | None = Query(None, description="Symbol filter"),
    limit: int = Query(500, ge=1, le=5000),
    _: None = Depends(require_any_role("trader", "risk_manager", "auditor")),
    session: Session = Depends(get_session),
) -> list[CashSettlementPriceRead]:
    return list_cash_settlement_prices_service(
        session,
        start_date=start_date,
        end_date=end_date,
        symbol=symbol,
        limit=limit,
    )


@router.post(
    "/aluminum/cash-settlement/ingest",
    response_model=CashSettlementIngestResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(RATE_LIMIT_SCRAPING)
def ingest_cash_settlement_daily(
    payload: CashSettlementIngestRequest,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="cash_settlement_price",
            event_type="ingested",
        )
    ),
    __: None = Depends(require_role("trader")),
    session: Session = Depends(get_session),
) -> CashSettlementIngestResponse:
    del request
    try:
        ingested_count, skipped_count, evidence = (
            ingest_westmetall_cash_settlement_daily_for_date(
                session, payload.settlement_date
            )
        )
    except WestmetallLayoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    except CircuitOpenError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    return CashSettlementIngestResponse(
        ingested_count=ingested_count,
        skipped_count=skipped_count,
        source=SOURCE_WESTMETALL,
        symbol=SYMBOL_DAILY,
        settlement_date=payload.settlement_date,
        source_url=evidence.source_url,
        html_sha256=evidence.html_sha256,
        fetched_at=evidence.fetched_at,
    )


@router.post(
    "/aluminum/cash-settlement/ingest-bulk",
    response_model=CashSettlementBulkIngestResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(RATE_LIMIT_SCRAPING)
def ingest_cash_settlement_bulk(
    payload: CashSettlementBulkIngestRequest,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="cash_settlement_price",
            event_type="bulk_ingested",
        )
    ),
    __: None = Depends(require_role("trader")),
    session: Session = Depends(get_session),
) -> CashSettlementBulkIngestResponse:
    del request
    try:
        ingested_count, skipped_count, evidence = (
            ingest_westmetall_cash_settlement_bulk(
                session,
                start_date=payload.start_date,
                end_date=payload.end_date,
            )
        )
    except WestmetallLayoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    except CircuitOpenError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    return CashSettlementBulkIngestResponse(
        ingested_count=ingested_count,
        skipped_count=skipped_count,
        source=SOURCE_WESTMETALL,
        symbol=SYMBOL_DAILY,
        source_url=evidence.source_url,
        html_sha256=evidence.html_sha256,
        fetched_at=evidence.fetched_at,
    )
