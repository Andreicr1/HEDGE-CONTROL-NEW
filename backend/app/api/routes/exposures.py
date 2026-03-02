from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_any_role
from app.core.database import get_session
from app.core.pagination import paginate
from app.models.exposure import (
    Exposure,
    ExposureStatus as ExposureStatusModel,
    HedgeTask,
    HedgeTaskStatus as HedgeTaskStatusModel,
)
from app.schemas.exposure import CommercialExposureRead, GlobalExposureRead
from app.schemas.exposure_engine import (
    ExposureDetailRead,
    ExposureListResponse,
    HedgeTaskListResponse,
    HedgeTaskRead,
    NetExposureResponse,
    ReconcileResponse,
)
from app.services.exposure_engine import ExposureEngineService
from app.services.exposure_service import ExposureService

router = APIRouter()


# ------------------------------------------------------------------
# Legacy endpoints (kept for backward compatibility)
# ------------------------------------------------------------------


@router.get("/commercial", response_model=CommercialExposureRead)
def get_commercial_exposure(
    _: None = Depends(require_any_role("risk_manager", "auditor")),
    session: Session = Depends(get_session),
) -> CommercialExposureRead:
    return ExposureService.compute_commercial_snapshot(session)


@router.get("/global", response_model=GlobalExposureRead)
def get_global_exposure(
    _: None = Depends(require_any_role("risk_manager", "auditor")),
    session: Session = Depends(get_session),
) -> GlobalExposureRead:
    return ExposureService.compute_global_snapshot(session)


# ------------------------------------------------------------------
# New Exposure Engine endpoints (1.3)
# ------------------------------------------------------------------


@router.post("/reconcile", response_model=ReconcileResponse)
def reconcile_exposures(
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    result = ExposureEngineService.reconcile_from_orders(session)
    return result


@router.get("/net", response_model=NetExposureResponse)
def get_net_exposure(
    commodity: Optional[str] = Query(None),
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    items = ExposureEngineService.compute_net_exposure(session, commodity)
    return {"items": items}


@router.get("/tasks", response_model=HedgeTaskListResponse)
def list_hedge_tasks(
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    q = (
        session.query(HedgeTask)
        .filter(HedgeTask.status == HedgeTaskStatusModel.pending)
        .order_by(HedgeTask.created_at.desc())
    )
    items, next_cursor = paginate(
        q,
        created_at_col=HedgeTask.created_at,
        id_col=HedgeTask.id,
        cursor=cursor,
        limit=limit,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.post("/tasks/{task_id}/execute")
def execute_hedge_task(
    task_id: UUID,
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    task = session.query(HedgeTask).filter(HedgeTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="HedgeTask not found"
        )
    if task.status != HedgeTaskStatusModel.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task is already {task.status.value}",
        )
    from datetime import datetime, timezone

    task.status = HedgeTaskStatusModel.executed
    task.executed_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(task)
    return HedgeTaskRead.model_validate(task)


# ------------------------------------------------------------------
# Exposure list (static path before /{id})
# ------------------------------------------------------------------


@router.get("/list", response_model=ExposureListResponse)
def list_exposures(
    commodity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    settlement_month: Optional[str] = Query(None),
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    q = session.query(Exposure).filter(Exposure.is_deleted == False)  # noqa: E712
    if commodity:
        q = q.filter(Exposure.commodity == commodity)
    if status_filter:
        q = q.filter(Exposure.status == ExposureStatusModel(status_filter))
    if settlement_month:
        q = q.filter(Exposure.settlement_month == settlement_month)
    q = q.order_by(Exposure.created_at.desc())

    items, next_cursor = paginate(
        q,
        created_at_col=Exposure.created_at,
        id_col=Exposure.id,
        cursor=cursor,
        limit=limit,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.get("/{exposure_id}", response_model=ExposureDetailRead)
def get_exposure(
    exposure_id: UUID,
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    exp = (
        session.query(Exposure)
        .filter(Exposure.id == exposure_id, Exposure.is_deleted == False)  # noqa: E712
        .first()
    )
    if not exp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Exposure not found"
        )
    return exp
