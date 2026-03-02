from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.auth import require_any_role, require_role
from app.core.database import get_session
from app.core.pagination import paginate
from app.core.rate_limit import RATE_LIMIT_MUTATION, limiter
from app.api.dependencies.audit import audit_event, mark_audit_success
from app.models.contracts import (
    HedgeClassification,
    HedgeContract,
    HedgeContractStatus,
    HedgeLegSide,
)
from app.schemas.contracts import (
    HedgeContractCreate,
    HedgeContractListResponse,
    HedgeContractRead,
    HedgeLegPriceType,
    HedgeLegSide,
)

router = APIRouter()


@router.post(
    "/hedge", response_model=HedgeContractRead, status_code=status.HTTP_201_CREATED
)
@limiter.limit(RATE_LIMIT_MUTATION)
def create_hedge_contract(
    payload: HedgeContractCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="hedge_contract",
            event_type="created",
        )
    ),
    __: None = Depends(require_role("trader")),
    session: Session = Depends(get_session),
) -> HedgeContractRead:
    fixed_leg = next(
        leg for leg in payload.legs if leg.price_type == HedgeLegPriceType.fixed
    )
    variable_leg = next(
        leg for leg in payload.legs if leg.price_type == HedgeLegPriceType.variable
    )
    classification = (
        HedgeClassification.long
        if fixed_leg.side == HedgeLegSide.buy
        else HedgeClassification.short
    )
    contract = HedgeContract(
        commodity=payload.commodity,
        quantity_mt=payload.quantity_mt,
        fixed_leg_side=HedgeLegSide(fixed_leg.side.value),
        variable_leg_side=HedgeLegSide(variable_leg.side.value),
        classification=classification,
        status=HedgeContractStatus.active,
    )
    session.add(contract)
    session.commit()
    session.refresh(contract)
    mark_audit_success(request, contract.id)
    request.state.audit_commit()
    return HedgeContractRead.model_validate(contract)


@router.get("/hedge", response_model=HedgeContractListResponse)
def list_hedge_contracts(
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status (active, cancelled, settled)",
    ),
    classification: str | None = Query(
        None, description="Filter by classification (long or short)"
    ),
    commodity: str | None = Query(None, description="Filter by commodity"),
    include_deleted: bool = Query(False, description="Include soft-deleted records"),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _: None = Depends(require_any_role("trader", "risk_manager", "auditor")),
    session: Session = Depends(get_session),
) -> HedgeContractListResponse:
    query = session.query(HedgeContract)
    if not include_deleted:
        query = query.filter(HedgeContract.deleted_at.is_(None))
    if status_filter:
        query = query.filter(HedgeContract.status == HedgeContractStatus(status_filter))
    if classification:
        query = query.filter(
            HedgeContract.classification == HedgeClassification(classification)
        )
    if commodity:
        query = query.filter(HedgeContract.commodity == commodity)
    items, next_cursor = paginate(
        query,
        created_at_col=HedgeContract.created_at,
        id_col=HedgeContract.id,
        cursor=cursor,
        limit=limit,
    )
    return HedgeContractListResponse(
        items=[HedgeContractRead.model_validate(c) for c in items],
        next_cursor=next_cursor,
    )


@router.get("/hedge/{contract_id}", response_model=HedgeContractRead)
def get_hedge_contract(
    contract_id: UUID, session: Session = Depends(get_session)
) -> HedgeContractRead:
    contract = session.get(HedgeContract, contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hedge contract not found"
        )
    return HedgeContractRead.model_validate(contract)


@router.patch("/hedge/{contract_id}/archive", response_model=HedgeContractRead)
@limiter.limit(RATE_LIMIT_MUTATION)
def archive_hedge_contract(
    contract_id: UUID,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="hedge_contract",
            event_type="archived",
        )
    ),
    __: None = Depends(require_role("trader")),
    session: Session = Depends(get_session),
) -> HedgeContractRead:
    contract = session.get(HedgeContract, contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Hedge contract not found"
        )
    if contract.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hedge contract already archived",
        )
    contract.deleted_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(contract)
    mark_audit_success(request, contract.id)
    request.state.audit_commit()
    return HedgeContractRead.model_validate(contract)
