from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import require_role
from app.core.database import get_session
from app.api.dependencies.audit import audit_event, mark_audit_success
from app.models.contracts import HedgeContract
from app.models.linkages import HedgeOrderLinkage
from app.models.orders import Order
from app.schemas.linkages import HedgeOrderLinkageCreate, HedgeOrderLinkageRead

router = APIRouter()


@router.post("", response_model=HedgeOrderLinkageRead, status_code=status.HTTP_201_CREATED)
def create_linkage(
    payload: HedgeOrderLinkageCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="linkage",
            event_type="created",
        )
    ),
    __: None = Depends(require_role("trader")),
    session: Session = Depends(get_session),
) -> HedgeOrderLinkageRead:
    order = session.get(Order, payload.order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    contract = session.get(HedgeContract, payload.contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hedge contract not found")

    order_linked_qty = (
        session.query(func.coalesce(func.sum(HedgeOrderLinkage.quantity_mt), 0.0))
        .filter(HedgeOrderLinkage.order_id == payload.order_id)
        .scalar()
    )
    contract_linked_qty = (
        session.query(func.coalesce(func.sum(HedgeOrderLinkage.quantity_mt), 0.0))
        .filter(HedgeOrderLinkage.contract_id == payload.contract_id)
        .scalar()
    )

    if float(order_linked_qty or 0.0) + payload.quantity_mt > order.quantity_mt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Linkage exceeds order quantity")

    if float(contract_linked_qty or 0.0) + payload.quantity_mt > contract.quantity_mt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Linkage exceeds contract quantity",
        )

    linkage = HedgeOrderLinkage(
        order_id=payload.order_id,
        contract_id=payload.contract_id,
        quantity_mt=payload.quantity_mt,
    )
    session.add(linkage)
    session.commit()
    session.refresh(linkage)
    mark_audit_success(request, linkage.id)
    request.state.audit_commit()
    return HedgeOrderLinkageRead.model_validate(linkage)


@router.get("/{linkage_id}", response_model=HedgeOrderLinkageRead)
def get_linkage(linkage_id: UUID, session: Session = Depends(get_session)) -> HedgeOrderLinkageRead:
    linkage = session.get(HedgeOrderLinkage, linkage_id)
    if not linkage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linkage not found")
    return HedgeOrderLinkageRead.model_validate(linkage)
