"""Routes for Finance Pipeline."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_session
from app.schemas.finance_pipeline import (
    PipelineRunDetailRead,
    PipelineRunListResponse,
    PipelineRunRead,
    TriggerPipelineRequest,
)
from app.services.finance_pipeline_service import FinancePipelineService

router = APIRouter()


@router.post(
    "/run", response_model=PipelineRunRead, status_code=status.HTTP_201_CREATED
)
def trigger_pipeline(
    body: TriggerPipelineRequest,
    db: Session = Depends(get_session),
    _user: dict = Depends(get_current_user),
):
    run = FinancePipelineService.run_daily_pipeline(db, body.run_date)
    return run


@router.get("/runs", response_model=PipelineRunListResponse)
def list_runs(
    limit: int = 50,
    db: Session = Depends(get_session),
    _user: dict = Depends(get_current_user),
):
    runs = FinancePipelineService.list_runs(db, limit=limit)
    return {"items": runs}


@router.get("/runs/{run_id}", response_model=PipelineRunDetailRead)
def get_run_detail(
    run_id: uuid.UUID,
    db: Session = Depends(get_session),
    _user: dict = Depends(get_current_user),
):
    run = FinancePipelineService.get_run(db, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found"
        )
    return run
