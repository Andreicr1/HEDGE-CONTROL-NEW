"""Routes for Hedge CRUD + lifecycle (1.4)."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.pagination import paginate
from app.models.hedge import Hedge
from app.schemas.hedge import (
    HedgeCreate,
    HedgeListResponse,
    HedgeRead,
    HedgeStatusUpdate,
    HedgeUpdate,
)
from app.services.hedge_service import HedgeService

router = APIRouter()


# ------------------------------------------------------------------
# Static paths first
# ------------------------------------------------------------------


@router.post(
    "/from-rfq/{rfq_id}", response_model=HedgeRead, status_code=status.HTTP_201_CREATED
)
def create_hedge_from_rfq(
    rfq_id: UUID,
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    created_by = user.get("preferred_username", user.get("sub", "unknown"))
    hedge = HedgeService.create_from_rfq_award(session, rfq_id, created_by=created_by)
    return hedge


@router.get("", response_model=HedgeListResponse)
def list_hedges(
    commodity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    counterparty_id: Optional[UUID] = Query(None),
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    q = HedgeService.list_hedges(session, commodity, status_filter, counterparty_id)
    items, next_cursor = paginate(
        q,
        created_at_col=Hedge.created_at,
        id_col=Hedge.id,
        cursor=cursor,
        limit=limit,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.post("", response_model=HedgeRead, status_code=status.HTTP_201_CREATED)
def create_hedge(
    body: HedgeCreate,
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    created_by = user.get("preferred_username", user.get("sub", "unknown"))
    data = body.model_dump()
    # Convert enum values to strings for service
    if data.get("direction"):
        data["direction"] = (
            data["direction"].value
            if hasattr(data["direction"], "value")
            else data["direction"]
        )
    if data.get("source_type"):
        data["source_type"] = (
            data["source_type"].value
            if hasattr(data["source_type"], "value")
            else data["source_type"]
        )
    hedge = HedgeService.create_hedge(session, data, created_by=created_by)
    return hedge


# ------------------------------------------------------------------
# Path-parameter routes
# ------------------------------------------------------------------


@router.get("/{hedge_id}", response_model=HedgeRead)
def get_hedge(
    hedge_id: UUID,
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    hedge = HedgeService.get_by_id(session, hedge_id)
    if not hedge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hedge not found"
        )
    return hedge


@router.patch("/{hedge_id}", response_model=HedgeRead)
def update_hedge(
    hedge_id: UUID,
    body: HedgeUpdate,
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = body.model_dump(exclude_unset=True)
    return HedgeService.update_hedge(session, hedge_id, data)


@router.patch("/{hedge_id}/status", response_model=HedgeRead)
def update_hedge_status(
    hedge_id: UUID,
    body: HedgeStatusUpdate,
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    from app.models.hedge import HedgeStatus as HedgeStatusModel

    return HedgeService.update_status(
        session, hedge_id, HedgeStatusModel(body.status.value)
    )


@router.delete("/{hedge_id}", response_model=HedgeRead)
def delete_hedge(
    hedge_id: UUID,
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return HedgeService.cancel_hedge(session, hedge_id)
