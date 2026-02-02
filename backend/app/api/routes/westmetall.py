from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.api.dependencies.audit import audit_event
from app.services.cash_settlement_prices import ingest_westmetall_cash_settlement_daily_for_date
from app.services.westmetall_cash_settlement import (
    SOURCE_WESTMETALL,
    SYMBOL_DAILY,
    WestmetallLayoutError,
)
from app.schemas.market_data import CashSettlementIngestRequest, CashSettlementIngestResponse


router = APIRouter()


@router.post(
    "/aluminum/cash-settlement/ingest",
    response_model=CashSettlementIngestResponse,
    status_code=status.HTTP_200_OK,
)
def ingest_cash_settlement_daily(
    payload: CashSettlementIngestRequest,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="cash_settlement_price",
            event_type="ingested",
        )
    ),
    session: Session = Depends(get_session),
) -> CashSettlementIngestResponse:
    del request
    try:
        ingested_count, skipped_count, evidence = ingest_westmetall_cash_settlement_daily_for_date(
            session, payload.settlement_date
        )
    except WestmetallLayoutError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

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

