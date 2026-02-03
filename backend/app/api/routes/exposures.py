from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import require_any_role, require_role
from app.core.database import get_session
from app.models.contracts import HedgeClassification, HedgeContract
from app.models.linkages import HedgeOrderLinkage
from app.models.orders import Order, OrderType, PriceType
from app.schemas.exposure import CommercialExposureRead, GlobalExposureRead

router = APIRouter()


@router.get("/commercial", response_model=CommercialExposureRead)
def get_commercial_exposure(
    _: None = Depends(require_any_role("risk_manager", "auditor")),
    session: Session = Depends(get_session),
) -> CommercialExposureRead:
    pre_reduction_active = (
        session.query(func.coalesce(func.sum(Order.quantity_mt), 0.0))
        .filter(Order.order_type == OrderType.sales, Order.price_type == PriceType.variable)
        .scalar()
    )
    pre_reduction_passive = (
        session.query(func.coalesce(func.sum(Order.quantity_mt), 0.0))
        .filter(Order.order_type == OrderType.purchase, Order.price_type == PriceType.variable)
        .scalar()
    )

    linked_by_order = (
        session.query(
            HedgeOrderLinkage.order_id.label("order_id"),
            func.coalesce(func.sum(HedgeOrderLinkage.quantity_mt), 0.0).label("linked_qty"),
        )
        .group_by(HedgeOrderLinkage.order_id)
        .subquery()
    )

    residual_quantity = Order.quantity_mt - func.coalesce(linked_by_order.c.linked_qty, 0.0)

    min_residual = (
        session.query(func.min(residual_quantity))
        .outerjoin(linked_by_order, Order.id == linked_by_order.c.order_id)
        .filter(Order.price_type == PriceType.variable)
        .scalar()
    )
    if min_residual is not None and float(min_residual) < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Residual exposure cannot be negative",
        )

    residual_active = (
        session.query(func.coalesce(func.sum(residual_quantity), 0.0))
        .outerjoin(linked_by_order, Order.id == linked_by_order.c.order_id)
        .filter(Order.order_type == OrderType.sales, Order.price_type == PriceType.variable)
        .scalar()
    )
    residual_passive = (
        session.query(func.coalesce(func.sum(residual_quantity), 0.0))
        .outerjoin(linked_by_order, Order.id == linked_by_order.c.order_id)
        .filter(Order.order_type == OrderType.purchase, Order.price_type == PriceType.variable)
        .scalar()
    )

    reduction_active = (
        session.query(func.coalesce(func.sum(linked_by_order.c.linked_qty), 0.0))
        .select_from(Order)
        .outerjoin(linked_by_order, Order.id == linked_by_order.c.order_id)
        .filter(Order.order_type == OrderType.sales, Order.price_type == PriceType.variable)
        .scalar()
    )
    reduction_passive = (
        session.query(func.coalesce(func.sum(linked_by_order.c.linked_qty), 0.0))
        .select_from(Order)
        .outerjoin(linked_by_order, Order.id == linked_by_order.c.order_id)
        .filter(Order.order_type == OrderType.purchase, Order.price_type == PriceType.variable)
        .scalar()
    )

    order_count_considered = (
        session.query(func.count(Order.id))
        .filter(Order.price_type == PriceType.variable)
        .scalar()
    )

    pre_active_value = float(pre_reduction_active or 0.0)
    pre_passive_value = float(pre_reduction_passive or 0.0)
    reduction_active_value = float(reduction_active or 0.0)
    reduction_passive_value = float(reduction_passive or 0.0)
    residual_active_value = float(residual_active or 0.0)
    residual_passive_value = float(residual_passive or 0.0)

    return CommercialExposureRead(
        pre_reduction_commercial_active_mt=pre_active_value,
        pre_reduction_commercial_passive_mt=pre_passive_value,
        reduction_applied_active_mt=reduction_active_value,
        reduction_applied_passive_mt=reduction_passive_value,
        commercial_active_mt=residual_active_value,
        commercial_passive_mt=residual_passive_value,
        commercial_net_mt=residual_active_value - residual_passive_value,
        calculation_timestamp=datetime.now(timezone.utc),
        order_count_considered=int(order_count_considered or 0),
    )


@router.get("/global", response_model=GlobalExposureRead)
def get_global_exposure(
    _: None = Depends(require_any_role("risk_manager", "auditor")),
    session: Session = Depends(get_session),
) -> GlobalExposureRead:
    pre_reduction_active = (
        session.query(func.coalesce(func.sum(Order.quantity_mt), 0.0))
        .filter(Order.order_type == OrderType.sales, Order.price_type == PriceType.variable)
        .scalar()
    )
    pre_reduction_passive = (
        session.query(func.coalesce(func.sum(Order.quantity_mt), 0.0))
        .filter(Order.order_type == OrderType.purchase, Order.price_type == PriceType.variable)
        .scalar()
    )

    linked_by_order = (
        session.query(
            HedgeOrderLinkage.order_id.label("order_id"),
            func.coalesce(func.sum(HedgeOrderLinkage.quantity_mt), 0.0).label("linked_qty"),
        )
        .group_by(HedgeOrderLinkage.order_id)
        .subquery()
    )

    residual_order_qty = Order.quantity_mt - func.coalesce(linked_by_order.c.linked_qty, 0.0)
    min_order_residual = (
        session.query(func.min(residual_order_qty))
        .outerjoin(linked_by_order, Order.id == linked_by_order.c.order_id)
        .filter(Order.price_type == PriceType.variable)
        .scalar()
    )
    if min_order_residual is not None and float(min_order_residual) < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Residual exposure cannot be negative",
        )

    reduced_commercial_active = (
        session.query(func.coalesce(func.sum(residual_order_qty), 0.0))
        .outerjoin(linked_by_order, Order.id == linked_by_order.c.order_id)
        .filter(Order.order_type == OrderType.sales, Order.price_type == PriceType.variable)
        .scalar()
    )
    reduced_commercial_passive = (
        session.query(func.coalesce(func.sum(residual_order_qty), 0.0))
        .outerjoin(linked_by_order, Order.id == linked_by_order.c.order_id)
        .filter(Order.order_type == OrderType.purchase, Order.price_type == PriceType.variable)
        .scalar()
    )

    linked_by_contract = (
        session.query(
            HedgeOrderLinkage.contract_id.label("contract_id"),
            func.coalesce(func.sum(HedgeOrderLinkage.quantity_mt), 0.0).label("linked_qty"),
        )
        .group_by(HedgeOrderLinkage.contract_id)
        .subquery()
    )

    residual_contract_qty = HedgeContract.quantity_mt - func.coalesce(
        linked_by_contract.c.linked_qty, 0.0
    )
    min_contract_residual = (
        session.query(func.min(residual_contract_qty))
        .outerjoin(linked_by_contract, HedgeContract.id == linked_by_contract.c.contract_id)
        .scalar()
    )
    if min_contract_residual is not None and float(min_contract_residual) < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Residual hedge quantity cannot be negative",
        )

    unlinked_hedge_long = (
        session.query(func.coalesce(func.sum(residual_contract_qty), 0.0))
        .outerjoin(linked_by_contract, HedgeContract.id == linked_by_contract.c.contract_id)
        .filter(HedgeContract.classification == HedgeClassification.long)
        .scalar()
    )
    unlinked_hedge_short = (
        session.query(func.coalesce(func.sum(residual_contract_qty), 0.0))
        .outerjoin(linked_by_contract, HedgeContract.id == linked_by_contract.c.contract_id)
        .filter(HedgeContract.classification == HedgeClassification.short)
        .scalar()
    )

    total_hedge_long = (
        session.query(func.coalesce(func.sum(HedgeContract.quantity_mt), 0.0))
        .filter(HedgeContract.classification == HedgeClassification.long)
        .scalar()
    )
    total_hedge_short = (
        session.query(func.coalesce(func.sum(HedgeContract.quantity_mt), 0.0))
        .filter(HedgeContract.classification == HedgeClassification.short)
        .scalar()
    )

    order_count_considered = (
        session.query(func.count(Order.id))
        .filter(Order.price_type == PriceType.variable)
        .scalar()
    )
    hedge_count_considered = session.query(func.count(HedgeContract.id)).scalar()
    entities_count = int(order_count_considered or 0) + int(hedge_count_considered or 0)

    pre_active_value = float(pre_reduction_active or 0.0)
    pre_passive_value = float(pre_reduction_passive or 0.0)
    reduced_active_value = float(reduced_commercial_active or 0.0)
    reduced_passive_value = float(reduced_commercial_passive or 0.0)
    total_hedge_long_value = float(total_hedge_long or 0.0)
    total_hedge_short_value = float(total_hedge_short or 0.0)
    unlinked_hedge_long_value = float(unlinked_hedge_long or 0.0)
    unlinked_hedge_short_value = float(unlinked_hedge_short or 0.0)

    pre_global_active = pre_active_value + total_hedge_short_value
    pre_global_passive = pre_passive_value + total_hedge_long_value
    post_global_active = reduced_active_value + unlinked_hedge_short_value
    post_global_passive = reduced_passive_value + unlinked_hedge_long_value

    return GlobalExposureRead(
        pre_reduction_global_active_mt=pre_global_active,
        pre_reduction_global_passive_mt=pre_global_passive,
        reduction_applied_active_mt=pre_global_active - post_global_active,
        reduction_applied_passive_mt=pre_global_passive - post_global_passive,
        global_active_mt=post_global_active,
        global_passive_mt=post_global_passive,
        global_net_mt=post_global_active - post_global_passive,
        commercial_active_mt=reduced_active_value,
        commercial_passive_mt=reduced_passive_value,
        hedge_long_mt=unlinked_hedge_long_value,
        hedge_short_mt=unlinked_hedge_short_value,
        calculation_timestamp=datetime.now(timezone.utc),
        entities_count_considered=entities_count,
    )
