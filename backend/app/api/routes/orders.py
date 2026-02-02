from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.api.dependencies.audit import audit_event, mark_audit_success
from app.models.orders import Order, OrderPricingConvention, OrderType, PriceType
from app.schemas.orders import OrderRead, PurchaseOrderCreate, SalesOrderCreate

router = APIRouter()


@router.post("/sales", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_sales_order(
    payload: SalesOrderCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="order",
            event_type="created",
        )
    ),
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
    )
    if payload.price_type.value == PriceType.variable.value:
        if payload.pricing_convention is not None and payload.avg_entry_price is not None:
            order.pricing_convention = OrderPricingConvention(payload.pricing_convention.value)
            order.avg_entry_price = float(payload.avg_entry_price)
    session.add(order)
    session.commit()
    session.refresh(order)
    mark_audit_success(request, order.id)
    request.state.audit_commit()
    return OrderRead.model_validate(order)


@router.post("/purchase", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="order",
            event_type="created",
        )
    ),
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
    )
    if payload.price_type.value == PriceType.variable.value:
        if payload.pricing_convention is not None and payload.avg_entry_price is not None:
            order.pricing_convention = OrderPricingConvention(payload.pricing_convention.value)
            order.avg_entry_price = float(payload.avg_entry_price)
    session.add(order)
    session.commit()
    session.refresh(order)
    mark_audit_success(request, order.id)
    request.state.audit_commit()
    return OrderRead.model_validate(order)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: UUID, session: Session = Depends(get_session)) -> OrderRead:
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return OrderRead.model_validate(order)
