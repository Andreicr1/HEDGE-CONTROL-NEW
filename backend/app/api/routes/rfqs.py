from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.api.dependencies.audit import audit_event, mark_audit_success
from app.models.contracts import HedgeClassification, HedgeContract, HedgeLegSide
from app.models.linkages import HedgeOrderLinkage
from app.models.orders import Order, OrderType, PriceType
from app.models.quotes import RFQQuote
from app.models.rfqs import (
    RFQ,
    RFQDirection,
    RFQIntent,
    RFQInvitation,
    RFQInvitationChannel,
    RFQInvitationStatus,
    RFQSequence,
    RFQState,
    RFQStateEvent,
)
from app.schemas.rfq import (
    RFQCreate,
    RFQAwardRequest,
    RFQQuoteCreate,
    RFQQuoteRead,
    RFQRefreshRequest,
    RFQRejectRequest,
    RFQRead,
    RFQInvitationRead,
    SpreadRankingEntry,
    SpreadRankingFailureCode,
    SpreadRankingRead,
    TradeRankingEntry,
    TradeRankingFailureCode,
    TradeRankingRead,
)

router = APIRouter()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _canonicalize_fixed_price_unit(unit: str) -> str | None:
    normalized = unit.strip().upper().replace("/", "").replace("-", "").replace(" ", "")
    if normalized == "USDMT":
        return "USD/MT"
    return None


def _latest_trade_quotes(session: Session, rfq_id: UUID) -> dict[str, RFQQuote]:
    quotes = session.query(RFQQuote).filter(RFQQuote.rfq_id == rfq_id).all()
    return _select_latest_quotes_by_counterparty(quotes)


def _trade_ranking_payload(
    rfq: RFQ, latest_quotes: dict[str, RFQQuote]
) -> TradeRankingRead:
    if not latest_quotes:
        return TradeRankingRead(
            rfq_id=rfq.id,
            status="FAILURE",
            failure_code=TradeRankingFailureCode.no_eligible_quotes,
            failure_reason="Zero eligible quotes",
            ranking=[],
        )

    quotes = list(latest_quotes.values())
    canonical_units = []
    for q in quotes:
        canonical = _canonicalize_fixed_price_unit(q.fixed_price_unit)
        if not canonical:
            return TradeRankingRead(
                rfq_id=rfq.id,
                status="FAILURE",
                failure_code=TradeRankingFailureCode.non_comparable,
                failure_reason="Non-canonical fixed_price_unit",
                ranking=[],
            )
        canonical_units.append(canonical)

    if len(set(canonical_units)) != 1:
        return TradeRankingRead(
            rfq_id=rfq.id,
            status="FAILURE",
            failure_code=TradeRankingFailureCode.non_comparable,
            failure_reason="fixed_price_unit mismatch",
            ranking=[],
        )

    reverse = rfq.direction == RFQDirection.sell
    ordered = sorted(quotes, key=lambda q: float(q.fixed_price_value), reverse=reverse)
    values = [float(q.fixed_price_value) for q in ordered]
    if len(set(values)) != len(values):
        return TradeRankingRead(
            rfq_id=rfq.id,
            status="FAILURE",
            failure_code=TradeRankingFailureCode.tie,
            failure_reason="Tie detected",
            ranking=[],
        )

    ranking = [
        TradeRankingEntry(rank=i + 1, quote=RFQQuoteRead.model_validate(q)) for i, q in enumerate(ordered)
    ]
    return TradeRankingRead(rfq_id=rfq.id, status="SUCCESS", ranking=ranking)


def _contract_legs_from_rfq_direction(direction: RFQDirection) -> tuple[HedgeLegSide, HedgeLegSide, HedgeClassification]:
    if direction == RFQDirection.buy:
        fixed_side = HedgeLegSide.buy
        variable_side = HedgeLegSide.sell
        classification = HedgeClassification.long
    else:
        fixed_side = HedgeLegSide.sell
        variable_side = HedgeLegSide.buy
        classification = HedgeClassification.short
    return fixed_side, variable_side, classification


def _create_linkage(session: Session, order_id: UUID, contract_id: UUID, quantity_mt: float) -> HedgeOrderLinkage:
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    contract = session.get(HedgeContract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hedge contract not found")

    order_linked_qty = (
        session.query(func.coalesce(func.sum(HedgeOrderLinkage.quantity_mt), 0.0))
        .filter(HedgeOrderLinkage.order_id == order_id)
        .scalar()
    )
    contract_linked_qty = (
        session.query(func.coalesce(func.sum(HedgeOrderLinkage.quantity_mt), 0.0))
        .filter(HedgeOrderLinkage.contract_id == contract_id)
        .scalar()
    )

    if float(order_linked_qty or 0.0) + quantity_mt > order.quantity_mt:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Linkage exceeds order quantity")
    if float(contract_linked_qty or 0.0) + quantity_mt > contract.quantity_mt:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Linkage exceeds contract quantity")

    linkage = HedgeOrderLinkage(order_id=order_id, contract_id=contract_id, quantity_mt=quantity_mt)
    session.add(linkage)
    session.flush()
    return linkage


def _convention_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _compute_commercial_exposure_snapshot(session: Session) -> dict:
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Residual exposure cannot be negative")

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

    pre_active_value = float(pre_reduction_active or 0.0)
    pre_passive_value = float(pre_reduction_passive or 0.0)
    residual_active_value = float(residual_active or 0.0)
    residual_passive_value = float(residual_passive or 0.0)
    reduction_active_value = float(reduction_active or 0.0)
    reduction_passive_value = float(reduction_passive or 0.0)

    return {
        "pre_active_mt": pre_active_value,
        "pre_passive_mt": pre_passive_value,
        "post_active_mt": residual_active_value,
        "post_passive_mt": residual_passive_value,
        "reduction_active_mt": reduction_active_value,
        "reduction_passive_mt": reduction_passive_value,
        "timestamp": _now_utc(),
    }


def _select_latest_quotes_by_counterparty(quotes: list[RFQQuote]) -> dict[str, RFQQuote]:
    ordered = sorted(
        quotes,
        key=lambda q: (q.counterparty_id, q.received_at, q.created_at, str(q.id)),
        reverse=False,
    )
    latest: dict[str, RFQQuote] = {}
    current_counterparty: str | None = None
    best_for_counterparty: RFQQuote | None = None
    for quote in ordered:
        if current_counterparty is None:
            current_counterparty = quote.counterparty_id
            best_for_counterparty = quote
            continue
        if quote.counterparty_id != current_counterparty:
            if best_for_counterparty is not None:
                latest[current_counterparty] = best_for_counterparty
            current_counterparty = quote.counterparty_id
            best_for_counterparty = quote
            continue

        assert best_for_counterparty is not None
        if (quote.received_at, quote.created_at, str(quote.id)) > (
            best_for_counterparty.received_at,
            best_for_counterparty.created_at,
            str(best_for_counterparty.id),
        ):
            best_for_counterparty = quote

    if current_counterparty is not None and best_for_counterparty is not None:
        latest[current_counterparty] = best_for_counterparty
    return latest


@router.post("", response_model=RFQRead, status_code=status.HTTP_201_CREATED)
def create_rfq(
    payload: RFQCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="rfq",
            event_type="created",
        )
    ),
    session: Session = Depends(get_session),
) -> RFQRead:
    snapshot = _compute_commercial_exposure_snapshot(session)

    order: Order | None = None
    if payload.intent.value == RFQIntent.commercial_hedge.value:
        order = session.get(Order, payload.order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.price_type != PriceType.variable:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order must be variable-price")

        expected_direction = "SELL" if order.order_type == OrderType.sales else "BUY"
        if payload.direction.value != expected_direction:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RFQ direction mismatch for order type")

        residual_side = snapshot["post_active_mt"] if order.order_type == OrderType.sales else snapshot["post_passive_mt"]
        if payload.quantity_mt > float(residual_side):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RFQ quantity exceeds residual exposure")

    if payload.intent.value == RFQIntent.spread.value:
        buy_trade_rfq = session.get(RFQ, payload.buy_trade_id)
        sell_trade_rfq = session.get(RFQ, payload.sell_trade_id)
        if not buy_trade_rfq or not sell_trade_rfq:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Referenced trade RFQ not found")
        if buy_trade_rfq.intent == RFQIntent.spread or sell_trade_rfq.intent == RFQIntent.spread:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Referenced trade RFQ cannot be SPREAD")

    seq = RFQSequence()
    session.add(seq)
    session.flush()
    year = _now_utc().year
    rfq_number = f"RFQ-{year}-{int(seq.id):06d}"

    initial_state = RFQState.created
    if any(inv.send_status.value in ("queued", "sent") for inv in payload.invitations):
        initial_state = RFQState.sent

    rfq = RFQ(
        rfq_number=rfq_number,
        intent=RFQIntent(payload.intent.value),
        commodity=payload.commodity,
        quantity_mt=payload.quantity_mt,
        delivery_window_start=payload.delivery_window_start,
        delivery_window_end=payload.delivery_window_end,
        direction=RFQDirection(payload.direction.value),
        order_id=payload.order_id,
        buy_trade_id=payload.buy_trade_id,
        sell_trade_id=payload.sell_trade_id,
        commercial_active_mt=snapshot["post_active_mt"],
        commercial_passive_mt=snapshot["post_passive_mt"],
        commercial_net_mt=snapshot["post_active_mt"] - snapshot["post_passive_mt"],
        commercial_reduction_applied_mt=snapshot["pre_active_mt"] - snapshot["post_active_mt"],
        exposure_snapshot_timestamp=snapshot["timestamp"],
        state=initial_state,
    )
    session.add(rfq)
    session.flush()

    for invitation in payload.invitations:
        session.add(
            RFQInvitation(
                rfq_id=rfq.id,
                rfq_number=rfq.rfq_number,
                recipient_id=invitation.recipient_id,
                recipient_name=invitation.recipient_name,
                channel=RFQInvitationChannel(invitation.channel.value),
                message_body=invitation.message_body,
                provider_message_id=invitation.provider_message_id,
                send_status=RFQInvitationStatus(invitation.send_status.value),
                sent_at=invitation.sent_at,
                idempotency_key=invitation.idempotency_key,
            )
        )

    if initial_state == RFQState.sent:
        session.add(RFQStateEvent(rfq_id=rfq.id, from_state=RFQState.created, to_state=RFQState.sent))

    session.commit()
    session.refresh(rfq)
    mark_audit_success(request, rfq.id)
    request.state.audit_commit()
    rfq_invitations = (
        session.query(RFQInvitation).filter(RFQInvitation.rfq_id == rfq.id).order_by(RFQInvitation.created_at.asc()).all()
    )

    rfq_read = RFQRead.model_validate(rfq)
    rfq_read.invitations = [RFQInvitationRead.model_validate(i) for i in rfq_invitations]
    return rfq_read


@router.get("/{rfq_id}", response_model=RFQRead)
def get_rfq(rfq_id: UUID, session: Session = Depends(get_session)) -> RFQRead:
    rfq = session.get(RFQ, rfq_id)
    if not rfq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")

    invitations = (
        session.query(RFQInvitation).filter(RFQInvitation.rfq_id == rfq_id).order_by(RFQInvitation.created_at).all()
    )
    rfq_read = RFQRead.model_validate(rfq)
    rfq_read.invitations = [RFQInvitationRead.model_validate(i) for i in invitations]
    return rfq_read


@router.post("/{rfq_id}/quotes", response_model=RFQQuoteRead, status_code=status.HTTP_201_CREATED)
def create_quote(
    rfq_id: UUID,
    payload: RFQQuoteCreate,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="rfq_quote",
            event_type="created",
        )
    ),
    session: Session = Depends(get_session),
) -> RFQQuoteRead:
    rfq = session.get(RFQ, rfq_id)
    if not rfq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")
    if rfq.intent == RFQIntent.spread:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SPREAD RFQ cannot receive quotes")
    if payload.rfq_id != rfq_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RFQ id mismatch")
    if rfq.state not in (RFQState.sent, RFQState.quoted):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="RFQ must be SENT before receiving quotes")

    quote = RFQQuote(
        rfq_id=rfq_id,
        counterparty_id=payload.counterparty_id,
        fixed_price_value=payload.fixed_price_value,
        fixed_price_unit=payload.fixed_price_unit,
        float_pricing_convention=payload.float_pricing_convention.value,
        received_at=payload.received_at,
    )
    session.add(quote)
    session.flush()

    if rfq.state == RFQState.sent:
        rfq.state = RFQState.quoted
        session.add(
            RFQStateEvent(
                rfq_id=rfq.id,
                from_state=RFQState.sent,
                to_state=RFQState.quoted,
                trigger="FIRST_ELIGIBLE_QUOTE_PERSISTED",
                triggering_quote_id=quote.id,
                triggering_counterparty_id=quote.counterparty_id,
                event_timestamp=_now_utc(),
            )
        )

    # If this trade RFQ is referenced by SPREAD RFQs, a SPREAD RFQ can become QUOTED
    # once at least one eligible counterparty exists across its buy/sell trade RFQs.
    parent_spreads = (
        session.query(RFQ)
        .filter(
            RFQ.intent == RFQIntent.spread,
            RFQ.state == RFQState.sent,
            (RFQ.buy_trade_id == rfq.id) | (RFQ.sell_trade_id == rfq.id),
        )
        .all()
    )
    for spread_rfq in parent_spreads:
        if spread_rfq.buy_trade_id is None or spread_rfq.sell_trade_id is None:
            continue
        buy_latest = _latest_trade_quotes(session, spread_rfq.buy_trade_id)
        sell_latest = _latest_trade_quotes(session, spread_rfq.sell_trade_id)
        if set(buy_latest.keys()) & set(sell_latest.keys()):
            spread_rfq.state = RFQState.quoted
            session.add(
                RFQStateEvent(
                    rfq_id=spread_rfq.id,
                    from_state=RFQState.sent,
                    to_state=RFQState.quoted,
                    trigger="FIRST_ELIGIBLE_QUOTE_PERSISTED",
                    triggering_quote_id=quote.id,
                    triggering_counterparty_id=quote.counterparty_id,
                    event_timestamp=_now_utc(),
                )
            )

    session.commit()
    session.refresh(quote)
    mark_audit_success(request, quote.id)
    request.state.audit_commit()
    return RFQQuoteRead.model_validate(quote)


@router.get("/{rfq_id}/trade-ranking", response_model=TradeRankingRead)
def get_trade_ranking(rfq_id: UUID, session: Session = Depends(get_session)) -> TradeRankingRead:
    rfq = session.get(RFQ, rfq_id)
    if not rfq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")

    if rfq.intent == RFQIntent.spread:
        return TradeRankingRead(
            rfq_id=rfq_id,
            status="FAILURE",
            failure_code=TradeRankingFailureCode.not_trade_intent,
            failure_reason="Trade ranking is not defined for intent=SPREAD",
            ranking=[],
        )

    latest = _latest_trade_quotes(session, rfq.id)
    return _trade_ranking_payload(rfq, latest)


@router.get("/{rfq_id}/ranking", response_model=SpreadRankingRead)
def get_spread_ranking(rfq_id: UUID, session: Session = Depends(get_session)) -> SpreadRankingRead:
    rfq = session.get(RFQ, rfq_id)
    if not rfq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")

    if rfq.intent != RFQIntent.spread:
        return SpreadRankingRead(
            rfq_id=rfq_id,
            status="FAILURE",
            failure_code=SpreadRankingFailureCode.not_spread_intent,
            failure_reason="Ranking is only defined for intent=SPREAD",
            ranking=[],
        )

    buy_rfq = session.get(RFQ, rfq.buy_trade_id) if rfq.buy_trade_id else None
    sell_rfq = session.get(RFQ, rfq.sell_trade_id) if rfq.sell_trade_id else None
    if not buy_rfq or not sell_rfq:
        return SpreadRankingRead(
            rfq_id=rfq_id,
            status="FAILURE",
            failure_code=SpreadRankingFailureCode.non_comparable,
            failure_reason="Referenced trade RFQ missing",
            ranking=[],
        )

    if buy_rfq.commodity != sell_rfq.commodity:
        return SpreadRankingRead(
            rfq_id=rfq_id,
            status="FAILURE",
            failure_code=SpreadRankingFailureCode.non_comparable,
            failure_reason="Trade RFQ commodity mismatch",
            ranking=[],
        )

    buy_quotes = session.query(RFQQuote).filter(RFQQuote.rfq_id == buy_rfq.id).all()
    sell_quotes = session.query(RFQQuote).filter(RFQQuote.rfq_id == sell_rfq.id).all()

    buy_latest = _select_latest_quotes_by_counterparty(buy_quotes)
    sell_latest = _select_latest_quotes_by_counterparty(sell_quotes)

    eligible_counterparties = sorted(set(buy_latest.keys()) & set(sell_latest.keys()))
    if not eligible_counterparties:
        return SpreadRankingRead(
            rfq_id=rfq_id,
            status="FAILURE",
            failure_code=SpreadRankingFailureCode.no_eligible_quotes,
            failure_reason="Zero eligible quotes",
            ranking=[],
        )

    spreads: list[tuple[str, float, RFQQuote, RFQQuote]] = []
    for cp in eligible_counterparties:
        buy_quote = buy_latest[cp]
        sell_quote = sell_latest[cp]

        buy_unit = _canonicalize_fixed_price_unit(buy_quote.fixed_price_unit)
        sell_unit = _canonicalize_fixed_price_unit(sell_quote.fixed_price_unit)
        if not buy_unit or not sell_unit:
            return SpreadRankingRead(
                rfq_id=rfq_id,
                status="FAILURE",
                failure_code=SpreadRankingFailureCode.non_comparable,
                failure_reason="Non-canonical fixed_price_unit",
                ranking=[],
            )
        if buy_unit != sell_unit:
            return SpreadRankingRead(
                rfq_id=rfq_id,
                status="FAILURE",
                failure_code=SpreadRankingFailureCode.non_comparable,
                failure_reason="fixed_price_unit mismatch between trades",
                ranking=[],
            )

        spreads.append((cp, float(sell_quote.fixed_price_value) - float(buy_quote.fixed_price_value), buy_quote, sell_quote))

    spread_values = [s[1] for s in spreads]
    if len(set(spread_values)) != len(spread_values):
        return SpreadRankingRead(
            rfq_id=rfq_id,
            status="FAILURE",
            failure_code=SpreadRankingFailureCode.tie,
            failure_reason="Tie detected",
            ranking=[],
        )

    ordered = sorted(spreads, key=lambda s: s[1], reverse=True)
    ranking: list[SpreadRankingEntry] = []
    for idx, (cp, spread_value, buy_quote, sell_quote) in enumerate(ordered, start=1):
        ranking.append(
            SpreadRankingEntry(
                rank=idx,
                counterparty_id=cp,
                spread_value=spread_value,
                buy_quote=RFQQuoteRead.model_validate(buy_quote),
                sell_quote=RFQQuoteRead.model_validate(sell_quote),
            )
        )

    return SpreadRankingRead(rfq_id=rfq_id, status="SUCCESS", ranking=ranking)


@router.post("/{rfq_id}/actions/reject", response_model=RFQRead)
def reject_rfq(
    rfq_id: UUID,
    payload: RFQRejectRequest,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="rfq",
            event_type="rejected",
        )
    ),
    session: Session = Depends(get_session),
) -> RFQRead:
    rfq = session.get(RFQ, rfq_id)
    if not rfq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")
    if rfq.state != RFQState.quoted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="RFQ must be in QUOTED state")

    rfq.state = RFQState.closed
    session.add(
        RFQStateEvent(
            rfq_id=rfq.id,
            from_state=RFQState.quoted,
            to_state=RFQState.closed,
            user_id=payload.user_id,
            reason="USER_REJECTED",
            event_timestamp=_now_utc(),
        )
    )
    session.commit()
    session.refresh(rfq)
    mark_audit_success(request, rfq.id)
    request.state.audit_commit()
    return get_rfq(rfq_id=rfq_id, session=session)


@router.post("/{rfq_id}/actions/refresh", response_model=RFQRead)
def refresh_rfq(
    rfq_id: UUID,
    payload: RFQRefreshRequest,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="rfq",
            event_type="refreshed",
        )
    ),
    session: Session = Depends(get_session),
) -> RFQRead:
    rfq = session.get(RFQ, rfq_id)
    if not rfq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")
    if rfq.state != RFQState.quoted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="RFQ must be in QUOTED state")

    existing = (
        session.query(RFQInvitation)
        .filter(RFQInvitation.rfq_id == rfq.id)
        .order_by(RFQInvitation.created_at.asc())
        .all()
    )
    recipients: dict[str, RFQInvitation] = {}
    for inv in existing:
        if inv.recipient_id not in recipients:
            recipients[inv.recipient_id] = inv

    if not recipients:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No recipients to refresh")

    message_body = f"RFQ#{rfq.rfq_number} — REFRESH: please resend your FIXED price quote."
    now = _now_utc()
    for recipient in recipients.values():
        session.add(
            RFQInvitation(
                rfq_id=rfq.id,
                rfq_number=rfq.rfq_number,
                recipient_id=recipient.recipient_id,
                recipient_name=recipient.recipient_name,
                channel=recipient.channel,
                message_body=message_body,
                provider_message_id=f"refresh-{rfq.rfq_number}-{recipient.recipient_id}",
                send_status=RFQInvitationStatus.queued,
                sent_at=now,
                idempotency_key=f"refresh-{rfq.rfq_number}-{recipient.recipient_id}",
            )
        )

    session.commit()
    session.refresh(rfq)
    mark_audit_success(request, rfq.id)
    request.state.audit_commit()
    return get_rfq(rfq_id=rfq_id, session=session)


@router.post("/{rfq_id}/actions/award", response_model=RFQRead)
def award_rfq(
    rfq_id: UUID,
    payload: RFQAwardRequest,
    request: Request,
    _: None = Depends(
        audit_event(
            entity_type="rfq",
            event_type="awarded",
        )
    ),
    session: Session = Depends(get_session),
) -> RFQRead:
    rfq = session.get(RFQ, rfq_id)
    if not rfq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found")
    if rfq.state != RFQState.quoted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="RFQ must be in QUOTED state")

    award_time = _now_utc()
    created_contract_ids: list[str] = []
    winning_quote_ids: list[str] = []
    winning_counterparty_ids: list[str] = []
    ranking_snapshot: dict

    if rfq.intent == RFQIntent.spread:
        ranking_payload = get_spread_ranking(rfq_id=rfq.id, session=session)
        if ranking_payload.status != "SUCCESS" or not ranking_payload.ranking:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ranking is not awardable")

        top = ranking_payload.ranking[0]
        winning_counterparty_ids = [top.counterparty_id]
        winning_quote_ids = [str(top.buy_quote.id), str(top.sell_quote.id)]
        ranking_snapshot = ranking_payload.model_dump(mode="json")

        for trade_rfq_id, quote in ((rfq.buy_trade_id, top.buy_quote), (rfq.sell_trade_id, top.sell_quote)):
            assert trade_rfq_id is not None
            trade_rfq = session.get(RFQ, trade_rfq_id)
            if not trade_rfq:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Referenced trade RFQ missing")

            fixed_side, variable_side, classification = _contract_legs_from_rfq_direction(trade_rfq.direction)
            contract = HedgeContract(
                commodity=trade_rfq.commodity,
                quantity_mt=trade_rfq.quantity_mt,
                rfq_id=trade_rfq.id,
                rfq_quote_id=quote.id,
                counterparty_id=top.counterparty_id,
                fixed_price_value=quote.fixed_price_value,
                fixed_price_unit=quote.fixed_price_unit,
                float_pricing_convention=_convention_value(quote.float_pricing_convention),
                fixed_leg_side=fixed_side,
                variable_leg_side=variable_side,
                classification=classification,
            )
            session.add(contract)
            session.flush()
            created_contract_ids.append(str(contract.id))

            if trade_rfq.intent == RFQIntent.commercial_hedge and trade_rfq.order_id is not None:
                _create_linkage(session, trade_rfq.order_id, contract.id, trade_rfq.quantity_mt)

    else:
        latest = _latest_trade_quotes(session, rfq.id)
        trade_ranking = _trade_ranking_payload(rfq, latest)
        if trade_ranking.status != "SUCCESS" or not trade_ranking.ranking:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ranking is not awardable")

        top_quote = trade_ranking.ranking[0].quote
        winning_counterparty_ids = [top_quote.counterparty_id]
        winning_quote_ids = [str(top_quote.id)]
        ranking_snapshot = trade_ranking.model_dump(mode="json")

        fixed_side, variable_side, classification = _contract_legs_from_rfq_direction(rfq.direction)
        contract = HedgeContract(
            commodity=rfq.commodity,
            quantity_mt=rfq.quantity_mt,
            rfq_id=rfq.id,
            rfq_quote_id=top_quote.id,
            counterparty_id=top_quote.counterparty_id,
            fixed_price_value=top_quote.fixed_price_value,
            fixed_price_unit=top_quote.fixed_price_unit,
            float_pricing_convention=_convention_value(top_quote.float_pricing_convention),
            fixed_leg_side=fixed_side,
            variable_leg_side=variable_side,
            classification=classification,
        )
        session.add(contract)
        session.flush()
        created_contract_ids.append(str(contract.id))

        if rfq.intent == RFQIntent.commercial_hedge and rfq.order_id is not None:
            _create_linkage(session, rfq.order_id, contract.id, rfq.quantity_mt)

    rfq.state = RFQState.awarded
    session.add(
        RFQStateEvent(
            rfq_id=rfq.id,
            from_state=RFQState.quoted,
            to_state=RFQState.awarded,
            user_id=payload.user_id,
            winning_quote_ids=json.dumps(winning_quote_ids, sort_keys=True),
            winning_counterparty_ids=json.dumps(winning_counterparty_ids, sort_keys=True),
            ranking_snapshot=json.dumps(ranking_snapshot, sort_keys=True),
            award_timestamp=award_time,
            event_timestamp=award_time,
        )
    )

    rfq.state = RFQState.closed
    session.add(
        RFQStateEvent(
            rfq_id=rfq.id,
            from_state=RFQState.awarded,
            to_state=RFQState.closed,
            created_contract_ids=json.dumps(created_contract_ids, sort_keys=True),
            event_timestamp=_now_utc(),
        )
    )

    session.commit()
    session.refresh(rfq)
    mark_audit_success(request, rfq.id)
    request.state.audit_commit()
    return get_rfq(rfq_id=rfq_id, session=session)
