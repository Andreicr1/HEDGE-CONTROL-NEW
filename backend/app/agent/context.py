from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.agent.audit import get_latest_agent_activity
from app.models.quotes import RFQQuote
from app.schemas.rfq import RFQInvitationRead, RFQQuoteRead, RFQRead
from app.services.rfq_service import RFQService


def build_rfq_read_model(session: Session, rfq_id: UUID) -> RFQRead:
    rfq = RFQService.get(session, rfq_id)
    invitations = RFQService.get_invitations(session, rfq_id)
    rfq_read = RFQRead.model_validate(rfq)
    rfq_read.invitations = [RFQInvitationRead.model_validate(item) for item in invitations]
    rfq_read.latest_agent_activity = get_latest_agent_activity(
        session,
        entity_type="rfq",
        entity_id=rfq_id,
    )
    return rfq_read


def build_rfq_context(
    session: Session,
    rfq_id: UUID | None,
    _input_payload: dict,
) -> dict:
    if rfq_id is None:
        return {}

    rfq_read = build_rfq_read_model(session, rfq_id)
    quotes = (
        session.query(RFQQuote)
        .filter(RFQQuote.rfq_id == rfq_id)
        .order_by(RFQQuote.created_at)
        .all()
    )
    latest_quotes = RFQService.select_latest_quotes_by_counterparty(quotes)

    return {
        "entity_id": str(rfq_read.id),
        "entity_type": "rfq",
        "rfq": rfq_read.model_dump(mode="json"),
        "quote_count": len(quotes),
        "latest_quotes_by_counterparty": {
            counterparty_id: RFQQuoteRead.model_validate(quote).model_dump(mode="json")
            for counterparty_id, quote in latest_quotes.items()
        },
    }


def render_rfq_prompt_context(session: Session, rfq_id: UUID) -> str:
    context = build_rfq_context(session, rfq_id, {})
    rfq = context["rfq"]
    latest_activity = rfq.get("latest_agent_activity") or {}
    activity_summary = latest_activity.get("summary") or "none"
    return (
        f"RFQ: {rfq['rfq_number']}\n"
        f"Commodity: {rfq['commodity']}\n"
        f"Quantity: {rfq['quantity_mt']} MT\n"
        f"Direction: {rfq['direction']}\n"
        f"Delivery: {rfq['delivery_window_start']} to {rfq['delivery_window_end']}\n"
        f"State: {rfq['state']}\n"
        f"Invitations: {len(rfq.get('invitations', []))}\n"
        f"Quotes received: {context['quote_count']}\n"
        f"Latest automation: {activity_summary}"
    )
