from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.auth import require_any_role, require_role
from app.core.database import get_session
from app.api.dependencies.audit import audit_event, mark_audit_success
from app.models.pl import PLSnapshot
from app.schemas.pl import PLResultResponse, PLSnapshotCreate, PLSnapshotResponse
from app.services.pl_calculation_service import compute_pl
from app.services.pl_snapshot_service import create_pl_snapshot


router = APIRouter()


@router.get("/{entity_type}/{entity_id}", response_model=PLResultResponse)
def get_pl(
    entity_type: str,
    entity_id: UUID,
    period_start: date = Query(...),
    period_end: date = Query(...),
    _: None = Depends(require_any_role("risk_manager", "auditor")),
    session: Session = Depends(get_session),
) -> PLResultResponse:
    return compute_pl(session, entity_type, entity_id, period_start, period_end)


@router.post("/snapshots", response_model=PLSnapshotResponse, status_code=status.HTTP_201_CREATED)
def post_pl_snapshot(
    snapshot_in: PLSnapshotCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="pl_snapshot",
            event_type="created",
        )
    ),
    __: None = Depends(require_role("trader")),
    session: Session = Depends(get_session),
) -> PLSnapshotResponse:
    snapshot = create_pl_snapshot(
        db=session,
        entity_type=snapshot_in.entity_type,
        entity_id=snapshot_in.entity_id,
        period_start=snapshot_in.period_start,
        period_end=snapshot_in.period_end,
    )
    mark_audit_success(request, snapshot.id)
    request.state.audit_commit()
    return PLSnapshotResponse.model_validate(snapshot)


@router.get("/snapshots", response_model=PLSnapshotResponse)
def get_pl_snapshot(
    entity_type: str,
    entity_id: UUID,
    period_start: date = Query(...),
    period_end: date = Query(...),
    _: None = Depends(require_any_role("risk_manager", "auditor")),
    session: Session = Depends(get_session),
) -> PLSnapshotResponse:
    snapshot = (
        session.query(PLSnapshot)
        .filter(
            PLSnapshot.entity_type == entity_type,
            PLSnapshot.entity_id == entity_id,
            PLSnapshot.period_start == period_start,
            PLSnapshot.period_end == period_end,
        )
        .first()
    )
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="P&L snapshot not found")
    return PLSnapshotResponse.model_validate(snapshot)