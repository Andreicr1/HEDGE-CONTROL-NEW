from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.auth import require_any_role, require_role
from app.core.database import get_session
from app.core.pagination import paginate
from app.core.rate_limit import RATE_LIMIT_MUTATION, limiter
from app.api.dependencies.audit import audit_event, mark_audit_success
from app.models.orders import (
    Order,
    OrderPricingConvention,
    OrderType,
    PriceType,
    SoPoLink,
)
from app.schemas.orders import (
    OrderListResponse,
    OrderRead,
    PurchaseOrderCreate,
    SalesOrderCreate,
    SoPoLinkCreate,
    SoPoLinkListResponse,
    SoPoLinkRead,
)

router = APIRouter()


@router.post("/sales", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMIT_MUTATION)
def create_sales_order(
    payload: SalesOrderCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="order",
            event_type="created",
        )
    ),
    __: None = Depends(require_role("trader")),
    session: Session = Depends(get_session),
) -> OrderRead:
    if payload.price_type.value == PriceType.variable.value:
        if (payload.pricing_convention is None) != (payload.avg_entry_price is None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="pricing_convention and avg_entry_price must be provided together",
            )
    order = Order(
        order_type=OrderType.sales,
        price_type=PriceType(payload.price_type.value),
        quantity_mt=payload.quantity_mt,
        counterparty_id=payload.counterparty_id,
        pricing_type=payload.pricing_type,
        delivery_terms=payload.delivery_terms,
        delivery_date_start=payload.delivery_date_start,
        delivery_date_end=payload.delivery_date_end,
        payment_terms_days=payload.payment_terms_days,
        currency=payload.currency,
        notes=payload.notes,
    )
    if payload.price_type.value == PriceType.variable.value:
        if (
            payload.pricing_convention is not None
            and payload.avg_entry_price is not None
        ):
            order.pricing_convention = OrderPricingConvention(
                payload.pricing_convention.value
            )
            order.avg_entry_price = float(payload.avg_entry_price)
    session.add(order)
    session.commit()
    session.refresh(order)
    mark_audit_success(request, order.id)
    request.state.audit_commit()
    return OrderRead.model_validate(order)


@router.post("/purchase", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMIT_MUTATION)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="order",
            event_type="created",
        )
    ),
    __: None = Depends(require_role("trader")),
    session: Session = Depends(get_session),
) -> OrderRead:
    if payload.price_type.value == PriceType.variable.value:
        if (payload.pricing_convention is None) != (payload.avg_entry_price is None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="pricing_convention and avg_entry_price must be provided together",
            )
    order = Order(
        order_type=OrderType.purchase,
        price_type=PriceType(payload.price_type.value),
        quantity_mt=payload.quantity_mt,
        counterparty_id=payload.counterparty_id,
        pricing_type=payload.pricing_type,
        delivery_terms=payload.delivery_terms,
        delivery_date_start=payload.delivery_date_start,
        delivery_date_end=payload.delivery_date_end,
        payment_terms_days=payload.payment_terms_days,
        currency=payload.currency,
        notes=payload.notes,
    )
    if payload.price_type.value == PriceType.variable.value:
        if (
            payload.pricing_convention is not None
            and payload.avg_entry_price is not None
        ):
            order.pricing_convention = OrderPricingConvention(
                payload.pricing_convention.value
            )
            order.avg_entry_price = float(payload.avg_entry_price)
    session.add(order)
    session.commit()
    session.refresh(order)
    mark_audit_success(request, order.id)
    request.state.audit_commit()
    return OrderRead.model_validate(order)


@router.get("", response_model=OrderListResponse)
def list_orders(
    order_type: str | None = Query(None, description="Filter by order type (SO or PO)"),
    price_type: str | None = Query(
        None, description="Filter by price type (fixed or variable)"
    ),
    include_deleted: bool = Query(False, description="Include soft-deleted records"),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _: None = Depends(require_any_role("trader", "risk_manager", "auditor")),
    session: Session = Depends(get_session),
) -> OrderListResponse:
    query = session.query(Order)
    if not include_deleted:
        query = query.filter(Order.deleted_at.is_(None))
    if order_type:
        query = query.filter(Order.order_type == OrderType(order_type))
    if price_type:
        query = query.filter(Order.price_type == PriceType(price_type))
    items, next_cursor = paginate(
        query,
        created_at_col=Order.created_at,
        id_col=Order.id,
        cursor=cursor,
        limit=limit,
    )
    return OrderListResponse(
        items=[OrderRead.model_validate(o) for o in items],
        next_cursor=next_cursor,
    )


# --- SO ↔ PO Link routes (must be before /{order_id} to avoid path conflict) ---


@router.post("/links", response_model=SoPoLinkRead, status_code=status.HTTP_201_CREATED)
def create_sopo_link(
    payload: SoPoLinkCreate,
    _user: dict = Depends(require_any_role("trader", "risk_manager")),
    session: Session = Depends(get_session),
) -> SoPoLinkRead:
    so = session.get(Order, payload.sales_order_id)
    if not so or so.order_type != OrderType.sales:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid sales order"
        )
    po = session.get(Order, payload.purchase_order_id)
    if not po or po.order_type != OrderType.purchase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid purchase order"
        )
    existing = (
        session.query(SoPoLink)
        .filter(
            SoPoLink.sales_order_id == payload.sales_order_id,
            SoPoLink.purchase_order_id == payload.purchase_order_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Link already exists"
        )
    link = SoPoLink(
        sales_order_id=payload.sales_order_id,
        purchase_order_id=payload.purchase_order_id,
        linked_tons=payload.linked_tons,
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return SoPoLinkRead.model_validate(link)


@router.get("/links", response_model=SoPoLinkListResponse)
def list_sopo_links(
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _user: dict = Depends(require_any_role("trader", "risk_manager", "auditor")),
    session: Session = Depends(get_session),
) -> SoPoLinkListResponse:
    query = session.query(SoPoLink)
    items, next_cursor = paginate(
        query,
        created_at_col=SoPoLink.created_at,
        id_col=SoPoLink.id,
        cursor=cursor,
        limit=limit,
    )
    return SoPoLinkListResponse(
        items=[SoPoLinkRead.model_validate(link) for link in items],
        next_cursor=next_cursor,
    )


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: UUID, session: Session = Depends(get_session)) -> OrderRead:
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    return OrderRead.model_validate(order)


@router.patch("/{order_id}/archive", response_model=OrderRead)
@limiter.limit(RATE_LIMIT_MUTATION)
def archive_order(
    order_id: UUID,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="order",
            event_type="archived",
        )
    ),
    __: None = Depends(require_role("trader")),
    session: Session = Depends(get_session),
) -> OrderRead:
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    if order.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Order already archived"
        )
    order.deleted_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(order)
    mark_audit_success(request, order.id)
    request.state.audit_commit()
    return OrderRead.model_validate(order)
