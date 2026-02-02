from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.api.dependencies.audit import audit_event, mark_audit_success
from app.models.cashflow import CashFlowLedgerEntry
from app.schemas.cashflow import (
    CashFlowLedgerEntryRead,
    HedgeContractSettlementCreate,
    HedgeContractSettlementResponse,
)
from app.services.cashflow_ledger_service import SOURCE_EVENT_TYPE, ingest_hedge_contract_settlement


router = APIRouter()


@router.post("/contracts/{contract_id}/settle", response_model=HedgeContractSettlementResponse, status_code=status.HTTP_201_CREATED)
def settle_hedge_contract(
    contract_id: UUID,
    payload: HedgeContractSettlementCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="hedge_contract_settlement",
            event_type="settled",
        )
    ),
    session: Session = Depends(get_session),
) -> HedgeContractSettlementResponse:
    event, ledger_entries = ingest_hedge_contract_settlement(session, contract_id, payload)
    mark_audit_success(request, event.id)
    request.state.audit_commit()
    return HedgeContractSettlementResponse(
        event=event,
        ledger_entries=[CashFlowLedgerEntryRead.model_validate(entry) for entry in ledger_entries],
    )


@router.get("/ledger/hedge-contracts/{contract_id}", response_model=list[CashFlowLedgerEntryRead])
def list_ledger_entries_for_contract(
    contract_id: UUID,
    start: date | None = Query(None),
    end: date | None = Query(None),
    session: Session = Depends(get_session),
) -> list[CashFlowLedgerEntryRead]:
    query = session.query(CashFlowLedgerEntry).filter(CashFlowLedgerEntry.hedge_contract_id == contract_id)
    if start is not None:
        query = query.filter(CashFlowLedgerEntry.cashflow_date >= start)
    if end is not None:
        query = query.filter(CashFlowLedgerEntry.cashflow_date <= end)
    entries = query.order_by(CashFlowLedgerEntry.cashflow_date.asc(), CashFlowLedgerEntry.created_at.asc()).all()
    return [CashFlowLedgerEntryRead.model_validate(entry) for entry in entries]


@router.get("/ledger", response_model=list[CashFlowLedgerEntryRead])
def list_ledger_entries_by_event(
    source_event_id: UUID = Query(...),
    source_event_type: str = Query(SOURCE_EVENT_TYPE),
    session: Session = Depends(get_session),
) -> list[CashFlowLedgerEntryRead]:
    if source_event_type != SOURCE_EVENT_TYPE:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported source_event_type")
    entries = (
        session.query(CashFlowLedgerEntry)
        .filter(
            CashFlowLedgerEntry.source_event_type == source_event_type,
            CashFlowLedgerEntry.source_event_id == source_event_id,
        )
        .order_by(CashFlowLedgerEntry.leg_id.asc())
        .all()
    )
    return [CashFlowLedgerEntryRead.model_validate(entry) for entry in entries]