from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.api.dependencies.audit import audit_event, mark_audit_success
from app.models.mtm import MTMObjectType, MTMSnapshot
from app.schemas.mtm import MTMResultResponse, MTMSnapshotCreate, MTMSnapshotResponse
from app.services.mtm_contract_service import compute_mtm_for_contract
from app.services.mtm_order_service import compute_mtm_for_order
from app.services.mtm_snapshot_service import create_mtm_snapshot_for_contract, create_mtm_snapshot_for_order


router = APIRouter()


@router.get("/hedge-contracts/{contract_id}", response_model=MTMResultResponse)
def get_mtm_for_hedge_contract(
    contract_id: UUID,
    as_of_date: date = Query(...),
    session: Session = Depends(get_session),
) -> MTMResultResponse:
    return compute_mtm_for_contract(session, contract_id=contract_id, as_of_date=as_of_date)


@router.get("/orders/{order_id}", response_model=MTMResultResponse)
def get_mtm_for_order(
    order_id: UUID,
    as_of_date: date = Query(...),
    session: Session = Depends(get_session),
) -> MTMResultResponse:
    return compute_mtm_for_order(session, order_id=order_id, as_of_date=as_of_date)


@router.post("/snapshots", response_model=MTMSnapshotResponse, status_code=status.HTTP_201_CREATED)
def create_mtm_snapshot(
    payload: MTMSnapshotCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="mtm_snapshot",
            event_type="created",
        )
    ),
    session: Session = Depends(get_session),
) -> MTMSnapshotResponse:
    if payload.object_type == MTMObjectType.hedge_contract:
        snapshot = create_mtm_snapshot_for_contract(
            session,
            contract_id=UUID(payload.object_id),
            as_of_date=payload.as_of_date,
            correlation_id=payload.correlation_id,
        )
    elif payload.object_type == MTMObjectType.order:
        snapshot = create_mtm_snapshot_for_order(
            session,
            order_id=UUID(payload.object_id),
            as_of_date=payload.as_of_date,
            correlation_id=payload.correlation_id,
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported object_type")
    mark_audit_success(request, snapshot.id)
    request.state.audit_commit()
    return MTMSnapshotResponse.model_validate(snapshot)


@router.get("/snapshots", response_model=MTMSnapshotResponse)
def get_mtm_snapshot(
    object_type: MTMObjectType,
    object_id: UUID,
    as_of_date: date,
    session: Session = Depends(get_session),
) -> MTMSnapshotResponse:
    snapshot = (
        session.query(MTMSnapshot)
        .filter(
            MTMSnapshot.object_type == object_type,
            MTMSnapshot.object_id == object_id,
            MTMSnapshot.as_of_date == as_of_date,
        )
        .first()
    )
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MTM snapshot not found")
    return MTMSnapshotResponse.model_validate(snapshot)
