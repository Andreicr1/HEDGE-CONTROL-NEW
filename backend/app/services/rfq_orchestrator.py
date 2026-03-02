"""RFQ Orchestrator — coordinates the full RFQ lifecycle.

State transitions:
    CREATED → SENT     (auto, after WhatsApp messages dispatched)
    SENT    → QUOTED   (auto, after first quote parsed)
    QUOTED  → AWARDED  (manual, trader confirms)
    QUOTED  → CLOSED   (manual, trader rejects)
    AWARDED → CLOSED   (auto, after contract generated)

The orchestrator is the single coordination point that ties together:
- WhatsApp outbound (5.1)
- Webhook inbound / message queue (5.2)
- LLM Agent parsing (5.3)
- RFQ Service business logic (existing)

It does NOT replace the RFQ Service — it delegates to it.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.utils import now_utc
from app.models.rfqs import (
    RFQ,
    RFQInvitation,
    RFQInvitationChannel,
    RFQInvitationStatus,
    RFQState,
)
from app.schemas.llm import ParsedQuote
from app.schemas.rfq import RFQQuoteCreate, FloatPricingConvention
from app.schemas.whatsapp import WhatsAppInboundMessage
from app.services.llm_agent import LLMAgent, LLMUnavailableError
from app.services.rfq_service import RFQService
from app.services.whatsapp_service import WhatsAppService
from app.services.webhook_processor import dequeue_message

logger = get_logger()


class RFQOrchestrator:
    """Coordinates the automated RFQ flow end-to-end."""

    # ------------------------------------------------------------------
    # 1. Dispatch outbound WhatsApp for all whatsapp invitations
    # ------------------------------------------------------------------

    @staticmethod
    def dispatch_whatsapp_invitations(session: Session, rfq_id: UUID) -> dict[str, str]:
        """Send WhatsApp messages for all pending whatsapp invitations.

        Returns a dict mapping ``recipient_id → send_status``.
        """
        invitations = (
            session.query(RFQInvitation)
            .filter(
                RFQInvitation.rfq_id == rfq_id,
                RFQInvitation.channel == RFQInvitationChannel.whatsapp,
                RFQInvitation.send_status == RFQInvitationStatus.queued,
            )
            .all()
        )

        results: dict[str, str] = {}
        for inv in invitations:
            result = WhatsAppService.send_text_message(
                phone=inv.recipient_id,
                text=inv.message_body,
            )
            if result.success:
                inv.send_status = RFQInvitationStatus.sent
                inv.provider_message_id = (
                    result.provider_message_id or inv.provider_message_id
                )
                results[inv.recipient_id] = "sent"
            else:
                inv.send_status = RFQInvitationStatus.failed
                results[inv.recipient_id] = "failed"

            logger.info(
                "orchestrator_whatsapp_dispatch",
                rfq_id=str(rfq_id),
                recipient=inv.recipient_id,
                status=results[inv.recipient_id],
            )

        session.flush()
        return results

    # ------------------------------------------------------------------
    # 2. Process inbound messages from the webhook queue
    # ------------------------------------------------------------------

    @staticmethod
    def process_inbound_queue(session: Session) -> list[dict]:
        """Drain the inbound message queue and process each message.

        For each message:
        1. Find the matching RFQ by looking up invitations by sender phone.
        2. Parse the message via LLM Agent.
        3. If confidence >= 0.85 and intent is QUOTE, auto-create a quote.
        4. Otherwise, flag for human review.

        Returns a list of processing results for observability.
        """
        results: list[dict] = []

        while True:
            msg = dequeue_message()
            if msg is None:
                break

            result = RFQOrchestrator._process_single_message(session, msg)
            results.append(result)

        return results

    @staticmethod
    def _process_single_message(
        session: Session,
        msg: WhatsAppInboundMessage,
    ) -> dict:
        """Process one inbound WhatsApp message."""
        # Find the RFQ by matching sender phone to invitation recipient_id
        invitation = (
            session.query(RFQInvitation)
            .filter(
                RFQInvitation.recipient_id == msg.from_phone,
                RFQInvitation.channel == RFQInvitationChannel.whatsapp,
            )
            .order_by(RFQInvitation.created_at.desc())
            .first()
        )

        if not invitation:
            logger.warning(
                "orchestrator_no_matching_rfq",
                from_phone=msg.from_phone,
                message_id=msg.message_id,
            )
            return {
                "message_id": msg.message_id,
                "status": "no_matching_rfq",
                "from_phone": msg.from_phone,
            }

        rfq = session.get(RFQ, invitation.rfq_id)
        if not rfq or rfq.state not in (RFQState.sent, RFQState.quoted):
            logger.info(
                "orchestrator_rfq_not_quotable",
                rfq_id=str(invitation.rfq_id) if rfq else None,
                state=rfq.state.value if rfq else None,
            )
            return {
                "message_id": msg.message_id,
                "status": "rfq_not_quotable",
                "rfq_id": str(invitation.rfq_id),
            }

        # Build RFQ context for the LLM
        rfq_context = (
            f"RFQ: {rfq.rfq_number}\n"
            f"Commodity: {rfq.commodity}\n"
            f"Quantity: {rfq.quantity_mt} MT\n"
            f"Direction: {rfq.direction.value}\n"
            f"Delivery: {rfq.delivery_window_start} to {rfq.delivery_window_end}"
        )

        try:
            parsed = LLMAgent.parse_quote_message(
                rfq_context=rfq_context,
                raw_message=msg.text,
                sender_name=msg.sender_name or invitation.recipient_name,
            )
        except LLMUnavailableError as exc:
            logger.error(
                "orchestrator_llm_unavailable",
                rfq_id=str(rfq.id),
                error=str(exc),
            )
            return {
                "message_id": msg.message_id,
                "status": "llm_unavailable",
                "rfq_id": str(rfq.id),
            }

        logger.info(
            "orchestrator_llm_parsed",
            rfq_id=str(rfq.id),
            intent=parsed.intent.value,
            confidence=parsed.confidence,
        )

        if LLMAgent.should_auto_create_quote(parsed):
            return RFQOrchestrator._auto_create_quote(
                session, rfq, invitation, msg, parsed
            )

        # Below confidence threshold — flag for human review
        return {
            "message_id": msg.message_id,
            "status": "needs_human_review",
            "rfq_id": str(rfq.id),
            "intent": parsed.intent.value,
            "confidence": parsed.confidence,
            "parsed": parsed.model_dump(mode="json"),
        }

    @staticmethod
    def _auto_create_quote(
        session: Session,
        rfq: RFQ,
        invitation: RFQInvitation,
        msg: WhatsAppInboundMessage,
        parsed: ParsedQuote,
    ) -> dict:
        """Create a quote automatically from a high-confidence LLM parse."""
        convention = parsed.float_pricing_convention or "avg"
        try:
            float_conv = FloatPricingConvention(convention)
        except ValueError:
            float_conv = FloatPricingConvention.avg

        quote_payload = RFQQuoteCreate(
            rfq_id=rfq.id,
            counterparty_id=invitation.recipient_id,
            fixed_price_value=float(parsed.fixed_price_value or 0),
            fixed_price_unit=parsed.fixed_price_unit or "USD/MT",
            float_pricing_convention=float_conv,
            received_at=msg.timestamp,
        )

        try:
            quote = RFQService.submit_quote(session, rfq.id, quote_payload)
            session.commit()
            logger.info(
                "orchestrator_auto_quote_created",
                rfq_id=str(rfq.id),
                quote_id=str(quote.id),
                counterparty=invitation.recipient_id,
                price=float(parsed.fixed_price_value or 0),
            )
            return {
                "message_id": msg.message_id,
                "status": "auto_quote_created",
                "rfq_id": str(rfq.id),
                "quote_id": str(quote.id),
                "confidence": parsed.confidence,
            }
        except Exception as exc:
            logger.error(
                "orchestrator_auto_quote_failed",
                rfq_id=str(rfq.id),
                error=str(exc),
            )
            return {
                "message_id": msg.message_id,
                "status": "auto_quote_failed",
                "rfq_id": str(rfq.id),
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # 3. Notify counterparties of award/reject via WhatsApp
    # ------------------------------------------------------------------

    @staticmethod
    def notify_award(
        session: Session,
        rfq: RFQ,
        winning_counterparty_id: str,
        price: float,
        unit: str = "USD/MT",
        language: str = "pt_BR",
    ) -> None:
        """Send WhatsApp award notification to the winning counterparty."""
        invitation = (
            session.query(RFQInvitation)
            .filter(
                RFQInvitation.rfq_id == rfq.id,
                RFQInvitation.recipient_id == winning_counterparty_id,
                RFQInvitation.channel == RFQInvitationChannel.whatsapp,
            )
            .first()
        )
        if not invitation:
            logger.info("orchestrator_no_whatsapp_for_award", rfq_id=str(rfq.id))
            return

        message = LLMAgent.generate_outbound_message(
            action="award",
            language=language,
            recipient_name=invitation.recipient_name,
            rfq_number=rfq.rfq_number,
            price=price,
            unit=unit,
        )
        WhatsAppService.send_text_message(
            phone=invitation.recipient_id,
            text=message,
        )

    @staticmethod
    def notify_reject(
        session: Session,
        rfq: RFQ,
        language: str = "pt_BR",
    ) -> None:
        """Send WhatsApp rejection notification to all counterparties."""
        invitations = (
            session.query(RFQInvitation)
            .filter(
                RFQInvitation.rfq_id == rfq.id,
                RFQInvitation.channel == RFQInvitationChannel.whatsapp,
            )
            .all()
        )

        # Deduplicate by recipient_id (keep latest)
        seen: dict[str, RFQInvitation] = {}
        for inv in invitations:
            seen[inv.recipient_id] = inv

        for inv in seen.values():
            message = LLMAgent.generate_outbound_message(
                action="reject",
                language=language,
                recipient_name=inv.recipient_name,
                rfq_number=rfq.rfq_number,
            )
            WhatsAppService.send_text_message(phone=inv.recipient_id, text=message)

    # ------------------------------------------------------------------
    # 4. Check timeouts — called by the scheduled task
    # ------------------------------------------------------------------

    @staticmethod
    def check_rfq_timeouts(
        session: Session,
        timeout_hours: int = 24,
    ) -> list[str]:
        """Find RFQs past their response deadline and trigger ranking.

        Returns a list of RFQ IDs that were auto-ranked due to timeout.
        """
        from datetime import timedelta

        cutoff = now_utc() - timedelta(hours=timeout_hours)

        stale_rfqs = (
            session.query(RFQ)
            .filter(
                RFQ.state == RFQState.sent,
                RFQ.created_at <= cutoff,
                RFQ.deleted_at.is_(None),
            )
            .all()
        )

        timed_out_ids: list[str] = []
        for rfq in stale_rfqs:
            latest_quotes = RFQService.get_latest_trade_quotes(session, rfq.id)
            if latest_quotes:
                # Has some quotes — move to QUOTED for ranking
                rfq.state = RFQState.quoted
                from app.models.rfqs import RFQStateEvent

                session.add(
                    RFQStateEvent(
                        rfq_id=rfq.id,
                        from_state=RFQState.sent,
                        to_state=RFQState.quoted,
                        trigger="TIMEOUT_PARTIAL_RANKING",
                        event_timestamp=now_utc(),
                        reason=f"Timeout after {timeout_hours}h — partial quotes available",
                    )
                )
            else:
                # No quotes at all — close
                rfq.state = RFQState.closed
                from app.models.rfqs import RFQStateEvent

                session.add(
                    RFQStateEvent(
                        rfq_id=rfq.id,
                        from_state=RFQState.sent,
                        to_state=RFQState.closed,
                        trigger="TIMEOUT_NO_QUOTES",
                        event_timestamp=now_utc(),
                        reason=f"Timeout after {timeout_hours}h — no quotes received",
                    )
                )

            timed_out_ids.append(str(rfq.id))

        if timed_out_ids:
            session.commit()
            logger.info(
                "orchestrator_timeout_check",
                timed_out_count=len(timed_out_ids),
                rfq_ids=timed_out_ids,
            )

        return timed_out_ids

    # ------------------------------------------------------------------
    # 5. Send reminders for RFQs with low response rate
    # ------------------------------------------------------------------

    @staticmethod
    def send_reminders(
        session: Session,
        min_response_rate: float = 0.5,
    ) -> list[str]:
        """Send reminders for SENT RFQs where < 50% have responded.

        Returns a list of RFQ IDs for which reminders were sent.
        """
        sent_rfqs = (
            session.query(RFQ)
            .filter(
                RFQ.state == RFQState.sent,
                RFQ.deleted_at.is_(None),
            )
            .all()
        )

        reminded_ids: list[str] = []
        for rfq in sent_rfqs:
            invitations = (
                session.query(RFQInvitation)
                .filter(RFQInvitation.rfq_id == rfq.id)
                .all()
            )
            if not invitations:
                continue

            unique_recipients = {inv.recipient_id for inv in invitations}
            quotes = RFQService.get_latest_trade_quotes(session, rfq.id)
            responded = set(quotes.keys())
            response_rate = len(responded) / len(unique_recipients)

            if response_rate >= min_response_rate:
                continue

            # Send reminder to non-responders via WhatsApp
            for inv in invitations:
                if (
                    inv.recipient_id not in responded
                    and inv.channel == RFQInvitationChannel.whatsapp
                ):
                    message = LLMAgent.generate_outbound_message(
                        action="refresh",
                        recipient_name=inv.recipient_name,
                        rfq_number=rfq.rfq_number,
                    )
                    WhatsAppService.send_text_message(
                        phone=inv.recipient_id,
                        text=message,
                    )

            reminded_ids.append(str(rfq.id))
            logger.info(
                "orchestrator_reminder_sent",
                rfq_id=str(rfq.id),
                response_rate=response_rate,
                non_responders=len(unique_recipients - responded),
            )

        return reminded_ids
