"""Cashflow projection service — forward-looking settlement timeline.

Scans all open instruments with future settlement/delivery dates and projects
the expected cash inflows and outflows:

* Sales Orders (SO)  → inflow  (+qty × price)
* Purchase Orders (PO) → outflow (−qty × price)
* Hedge Contracts     → net of fixed vs. variable leg

For variable-price instruments the latest market price is used as estimate.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.contracts import HedgeClassification, HedgeContract, HedgeContractStatus
from app.models.deal import DealLink, DealLinkedType
from app.models.orders import Order, OrderType, PriceType
from app.schemas.cashflow import (
    CashFlowProjectionItem,
    CashFlowProjectionResponse,
    CashFlowProjectionSummary,
    ProjectionInstrumentType,
)

logger = logging.getLogger(__name__)


def _get_market_price(
    session: Session, commodity: str, as_of_date: date
) -> Decimal | None:
    try:
        from app.services.price_lookup_service import (
            get_cash_settlement_price_d1,
            resolve_symbol,
        )

        symbol = resolve_symbol(commodity)
        return Decimal(
            str(
                get_cash_settlement_price_d1(
                    session, symbol=symbol, as_of_date=as_of_date
                )
            )
        )
    except Exception:
        logger.debug(
            "market_price_unavailable commodity=%s date=%s", commodity, as_of_date
        )
        return None


def _resolve_deal_id(
    session: Session, linked_type: DealLinkedType, linked_id
) -> str | None:
    """Find the deal_id if this instrument is linked to a deal."""
    link = (
        session.query(DealLink)
        .filter(DealLink.linked_type == linked_type, DealLink.linked_id == linked_id)
        .first()
    )
    return str(link.deal_id) if link else None


def _order_settlement_date(order: Order) -> date | None:
    """Best available future date for an order."""
    if order.delivery_date_end:
        return (
            order.delivery_date_end
            if isinstance(order.delivery_date_end, date)
            else None
        )
    if order.delivery_date_start:
        return (
            order.delivery_date_start
            if isinstance(order.delivery_date_start, date)
            else None
        )
    return None


def compute_cashflow_projection(
    session: Session,
    as_of_date: date,
) -> CashFlowProjectionResponse:
    items: list[CashFlowProjectionItem] = []
    market_price = _get_market_price(session, "LME_AL", as_of_date)

    # ── Orders (SO + PO) ──
    orders = session.query(Order).filter(Order.deleted_at.is_(None)).all()
    for order in orders:
        settle_dt = _order_settlement_date(order)
        if settle_dt is None or settle_dt < as_of_date:
            continue

        qty = Decimal(str(order.quantity_mt))
        if order.price_type == PriceType.fixed:
            price = Decimal(str(order.avg_entry_price or 0))
            price_src = "fixed"
        elif market_price is not None:
            price = market_price
            price_src = "market"
        else:
            price = Decimal(str(order.avg_entry_price or 0))
            price_src = "entry"

        amount = qty * price
        is_so = order.order_type == OrderType.sales

        if is_so:
            instr_type = ProjectionInstrumentType.sales_order
            deal_type = DealLinkedType.sales_order
        else:
            instr_type = ProjectionInstrumentType.purchase_order
            deal_type = DealLinkedType.purchase_order
            amount = -amount

        items.append(
            CashFlowProjectionItem(
                instrument_type=instr_type,
                instrument_id=str(order.id),
                reference="",
                counterparty="",
                commodity="Al",
                settlement_date=settle_dt,
                quantity_mt=qty,
                price_per_mt=price,
                amount_usd=amount,
                price_source=price_src,
                deal_id=_resolve_deal_id(session, deal_type, order.id),
            )
        )

    # ── Hedge Contracts (active / partially_settled, not deleted) ──
    contracts = (
        session.query(HedgeContract)
        .filter(
            HedgeContract.status.in_(
                (
                    HedgeContractStatus.active,
                    HedgeContractStatus.partially_settled,
                )
            ),
            HedgeContract.deleted_at.is_(None),
        )
        .all()
    )
    for contract in contracts:
        settle_dt = contract.settlement_date or as_of_date
        if settle_dt < as_of_date:
            continue

        qty = Decimal(str(contract.quantity_mt))
        fixed_price = Decimal(str(contract.fixed_price_value or 0))

        if market_price is not None:
            est_variable = market_price
            price_src = "market"
        else:
            est_variable = fixed_price
            price_src = "entry"

        fixed_side = contract.fixed_leg_side.value
        if fixed_side == "buy":
            amount = qty * (est_variable - fixed_price)
        else:
            amount = qty * (fixed_price - est_variable)

        # Determine instrument type from classification
        if contract.classification == HedgeClassification.short:
            instr_type = ProjectionInstrumentType.hedge_sell
        else:
            instr_type = ProjectionInstrumentType.hedge_buy

        items.append(
            CashFlowProjectionItem(
                instrument_type=instr_type,
                instrument_id=str(contract.id),
                reference=contract.reference or "",
                counterparty=contract.counterparty_id or "",
                commodity=contract.commodity,
                settlement_date=settle_dt,
                quantity_mt=qty,
                price_per_mt=fixed_price,
                amount_usd=amount,
                price_source=price_src,
                deal_id=_resolve_deal_id(session, DealLinkedType.contract, contract.id),
            )
        )

    items.sort(key=lambda x: x.settlement_date)

    total_in = sum((it.amount_usd for it in items if it.amount_usd > 0), Decimal("0"))
    total_out = sum((it.amount_usd for it in items if it.amount_usd < 0), Decimal("0"))

    return CashFlowProjectionResponse(
        as_of_date=as_of_date,
        items=items,
        summary=CashFlowProjectionSummary(
            total_inflows=total_in,
            total_outflows=total_out,
            net_cashflow=total_in + total_out,
            instrument_count=len(items),
        ),
    )
