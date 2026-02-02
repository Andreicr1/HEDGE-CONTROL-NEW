from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.api.dependencies.audit import audit_event, mark_audit_success
from app.models.cashflow import CashFlowBaselineSnapshot
from app.schemas.cashflow import (
    CashFlowAnalyticResponse,
    CashFlowBaselineSnapshotCreate,
    CashFlowBaselineSnapshotResponse,
)
from app.services.cashflow_analytic_service import compute_cashflow_analytic
from app.services.cashflow_baseline_service import create_cashflow_baseline_snapshot


router = APIRouter()


@router.get("/analytic", response_model=CashFlowAnalyticResponse)
def get_cashflow_analytic(
    as_of_date: date = Query(...),
    session: Session = Depends(get_session),
) -> CashFlowAnalyticResponse:
    return compute_cashflow_analytic(session, as_of_date=as_of_date)


@router.post("/baseline/snapshots", response_model=CashFlowBaselineSnapshotResponse, status_code=status.HTTP_201_CREATED)
def create_baseline_snapshot(
    payload: CashFlowBaselineSnapshotCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="cashflow_baseline_snapshot",
            event_type="created",
        )
    ),
    session: Session = Depends(get_session),
) -> CashFlowBaselineSnapshotResponse:
    snapshot = create_cashflow_baseline_snapshot(
        session, as_of_date=payload.as_of_date, correlation_id=payload.correlation_id
    )
    mark_audit_success(request, snapshot.id)
    request.state.audit_commit()
    return CashFlowBaselineSnapshotResponse.model_validate(snapshot)


@router.get("/baseline/snapshots", response_model=CashFlowBaselineSnapshotResponse)
def get_baseline_snapshot(
    as_of_date: date = Query(...),
    session: Session = Depends(get_session),
) -> CashFlowBaselineSnapshotResponse:
    snapshot = session.query(CashFlowBaselineSnapshot).filter(CashFlowBaselineSnapshot.as_of_date == as_of_date).first()
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Baseline snapshot not found")
    return CashFlowBaselineSnapshotResponse.model_validate(snapshot)
