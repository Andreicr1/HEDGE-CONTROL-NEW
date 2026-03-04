"""Routes for Deal Engine (component 1.5)."""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_session
from app.core.pagination import paginate
from app.models.deal import Deal, DealLink, DealLinkedType
from app.schemas.deal import (
    DealCreate,
    DealDetailRead,
    DealLinkCreate,
    DealLinkRead,
    DealListResponse,
    DealPNLHistoryResponse,
    DealPNLSnapshotRead,
    DealRead,
    PnlBreakdownRequest,
    PnlBreakdownResponse,
)
from app.services.deal_engine import DealEngineService

router = APIRouter()


# ------------------------------------------------------------------
# Static paths first
# ------------------------------------------------------------------


@router.get("/by-linked-entity", response_model=DealRead)
def find_deal_by_linked_entity(
    linked_type: str = Query(..., description="e.g. sales_order, purchase_order"),
    linked_id: UUID = Query(...),
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Find the deal that contains a given linked entity (order or contract)."""
    try:
        resolved_type = DealLinkedType(linked_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid linked_type: {linked_type}",
        )
    link = (
        session.query(DealLink)
        .filter(DealLink.linked_type == resolved_type, DealLink.linked_id == linked_id)
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deal found for the given entity.",
        )
    deal = session.get(Deal, link.deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found.",
        )
    return deal


@router.post("", response_model=DealRead, status_code=status.HTTP_201_CREATED)
def create_deal(
    body: DealCreate,
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = body.model_dump()
    # Convert enum values in links
    if data.get("links"):
        for link in data["links"]:
            if hasattr(link.get("linked_type"), "value"):
                link["linked_type"] = link["linked_type"].value
    deal = DealEngineService.create_deal(session, data)
    return deal


@router.get("", response_model=DealListResponse)
def list_deals(
    commodity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    q = DealEngineService.list_deals(session, commodity, status_filter)
    items, next_cursor = paginate(
        q,
        created_at_col=Deal.created_at,
        id_col=Deal.id,
        cursor=cursor,
        limit=limit,
    )
    return {"items": items, "next_cursor": next_cursor}


@router.post("/pnl-breakdown", response_model=PnlBreakdownResponse)
def pnl_breakdown(
    body: PnlBreakdownRequest,
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Compute P&L breakdown for one, many, or all deals."""
    result = DealEngineService.compute_pnl_breakdown(
        session, body.deal_ids, body.snapshot_date
    )
    return result


# ------------------------------------------------------------------
# Path-parameter routes
# ------------------------------------------------------------------


@router.get("/{deal_id}", response_model=DealDetailRead)
def get_deal(
    deal_id: UUID,
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return DealEngineService.get_detail(session, deal_id)


@router.post(
    "/{deal_id}/links", response_model=DealLinkRead, status_code=status.HTTP_201_CREATED
)
def add_link(
    deal_id: UUID,
    body: DealLinkCreate,
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return DealEngineService.add_link(
        session, deal_id, body.linked_type.value, body.linked_id
    )


@router.delete("/{deal_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_link(
    deal_id: UUID,
    link_id: UUID,
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    DealEngineService.remove_link(session, deal_id, link_id)


@router.post(
    "/{deal_id}/pnl-snapshot",
    response_model=DealPNLSnapshotRead,
    status_code=status.HTTP_201_CREATED,
)
def trigger_pnl_snapshot(
    deal_id: UUID,
    snapshot_date: date = Query(default=None),
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if snapshot_date is None:
        snapshot_date = date.today()
    return DealEngineService.compute_deal_pnl(session, deal_id, snapshot_date)


@router.get("/{deal_id}/pnl-history", response_model=DealPNLHistoryResponse)
def pnl_history(
    deal_id: UUID,
    _user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    snapshots = DealEngineService.get_pnl_history(session, deal_id)
    return {"items": snapshots}
