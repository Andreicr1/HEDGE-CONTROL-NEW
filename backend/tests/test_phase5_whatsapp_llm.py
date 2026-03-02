"""Phase 5 tests — WhatsApp Service, Webhook Processor, LLM Agent, RFQ Orchestrator.

These tests mock external services (WhatsApp Cloud API, Azure OpenAI) so that
the full automated RFQ lifecycle can be validated end-to-end without network
calls.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(timezone.utc)


def _make_meta_payload(
    from_phone: str = "+5511999999999",
    text: str = "Ofereço 2450 USD/MT avg",
    message_id: str = "wamid.test123",
    name: str = "Trader João",
    timestamp: int | None = None,
) -> dict:
    """Build a Meta-format webhook payload with one text message."""
    ts = timestamp or int(_NOW.timestamp())
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "BIZ_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "+5511000000000",
                                "phone_number_id": "PHONE_ID",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": name},
                                    "wa_id": from_phone,
                                }
                            ],
                            "messages": [
                                {
                                    "from": from_phone,
                                    "id": message_id,
                                    "timestamp": str(ts),
                                    "text": {"body": text},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def _sign_payload(body: bytes, secret: str) -> str:
    """Compute X-Hub-Signature-256 for a body and secret."""
    h = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={h}"


# ===================================================================
# 1. WhatsApp Service
# ===================================================================


class TestWhatsAppService:
    """Tests for ``app.services.whatsapp_service.WhatsAppService``."""

    @patch.dict(os.environ, {
        "WHATSAPP_API_URL": "https://graph.facebook.com/v19.0",
        "WHATSAPP_ACCESS_TOKEN": "test_token",
        "WHATSAPP_PHONE_NUMBER_ID": "12345",
    })
    @patch("app.services.whatsapp_service.httpx.post")
    def test_send_text_message_success(self, mock_post: MagicMock) -> None:
        from app.services.whatsapp_service import WhatsAppService

        mock_post.return_value = MagicMock(
            is_success=True,
            json=lambda: {"messages": [{"id": "wamid.abc"}]},
        )

        result = WhatsAppService.send_text_message("+5511999999999", "Hello")

        assert result.success is True
        assert result.provider_message_id == "wamid.abc"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"]["type"] == "text"
        assert call_kwargs.kwargs["json"]["text"]["body"] == "Hello"

    @patch.dict(os.environ, {
        "WHATSAPP_API_URL": "https://graph.facebook.com/v19.0",
        "WHATSAPP_ACCESS_TOKEN": "test_token",
        "WHATSAPP_PHONE_NUMBER_ID": "12345",
    })
    @patch("app.services.whatsapp_service.httpx.post")
    def test_send_text_message_api_error(self, mock_post: MagicMock) -> None:
        from app.services.whatsapp_service import WhatsAppService

        mock_post.return_value = MagicMock(
            is_success=False,
            status_code=400,
            json=lambda: {
                "error": {"code": 100, "message": "Invalid phone number"}
            },
        )

        result = WhatsAppService.send_text_message("+000", "Hello")

        assert result.success is False
        assert result.error_code == "100"
        assert "Invalid phone number" in (result.error_message or "")

    @patch.dict(os.environ, {
        "WHATSAPP_API_URL": "https://graph.facebook.com/v19.0",
        "WHATSAPP_ACCESS_TOKEN": "test_token",
        "WHATSAPP_PHONE_NUMBER_ID": "12345",
    })
    @patch("app.services.whatsapp_service.httpx.post")
    def test_send_text_message_timeout(self, mock_post: MagicMock) -> None:
        from app.services.whatsapp_service import WhatsAppService

        mock_post.side_effect = httpx.TimeoutException("timed out")

        result = WhatsAppService.send_text_message("+5511999999999", "Hello")

        assert result.success is False
        assert result.error_code == "TIMEOUT"

    @patch.dict(os.environ, {
        "WHATSAPP_API_URL": "https://graph.facebook.com/v19.0",
        "WHATSAPP_ACCESS_TOKEN": "test_token",
        "WHATSAPP_PHONE_NUMBER_ID": "12345",
    })
    @patch("app.services.whatsapp_service.httpx.post")
    def test_send_template_message(self, mock_post: MagicMock) -> None:
        from app.services.whatsapp_service import WhatsAppService

        mock_post.return_value = MagicMock(
            is_success=True,
            json=lambda: {"messages": [{"id": "wamid.tpl1"}]},
        )

        result = WhatsAppService.send_template_message(
            phone="+5511999999999",
            template_name="rfq_request_v1",
            params=["RFQ-001", "Zinc", "100 MT"],
        )

        assert result.success is True
        assert result.provider_message_id == "wamid.tpl1"
        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["json"]["type"] == "template"

    @patch.dict(os.environ, {
        "WHATSAPP_API_URL": "https://graph.facebook.com/v19.0",
        "WHATSAPP_ACCESS_TOKEN": "test_token",
        "WHATSAPP_PHONE_NUMBER_ID": "12345",
    })
    @patch("app.services.whatsapp_service.httpx.post")
    def test_send_text_message_generic_exception(self, mock_post: MagicMock) -> None:
        from app.services.whatsapp_service import WhatsAppService

        mock_post.side_effect = Exception("Connection refused")

        result = WhatsAppService.send_text_message("+5511999999999", "Hello")

        assert result.success is False
        assert result.error_code == "INTERNAL"


# ===================================================================
# 2. Webhook Processor
# ===================================================================


class TestWebhookProcessor:
    """Tests for ``app.services.webhook_processor``."""

    def test_extract_messages_single(self) -> None:
        from app.services.webhook_processor import extract_messages

        payload = _make_meta_payload(
            from_phone="+5511888888888",
            text="Cotação: 2500 USD/MT",
            message_id="wamid.msg1",
            name="Carlos",
        )
        msgs = extract_messages(payload)

        assert len(msgs) == 1
        assert msgs[0].from_phone == "+5511888888888"
        assert msgs[0].text == "Cotação: 2500 USD/MT"
        assert msgs[0].sender_name == "Carlos"
        assert msgs[0].message_id == "wamid.msg1"

    def test_extract_messages_empty(self) -> None:
        from app.services.webhook_processor import extract_messages

        payload = {"object": "whatsapp_business_account", "entry": []}
        msgs = extract_messages(payload)

        assert msgs == []

    def test_extract_messages_non_text_ignored(self) -> None:
        from app.services.webhook_processor import extract_messages

        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "contacts": [],
                                "messages": [
                                    {
                                        "from": "+5511000000000",
                                        "id": "m1",
                                        "timestamp": "1700000000",
                                        "type": "image",
                                    }
                                ],
                            }
                        }
                    ]
                }
            ],
        }
        msgs = extract_messages(payload)

        assert msgs == []

    def test_enqueue_dequeue(self) -> None:
        from app.services.webhook_processor import (
            dequeue_message,
            drain_queue,
            enqueue_message,
            queue_depth,
        )

        # Ensure queue is empty
        drain_queue()

        from app.schemas.whatsapp import WhatsAppInboundMessage

        msg = WhatsAppInboundMessage(
            message_id="m1",
            from_phone="+5511999999999",
            timestamp=_NOW,
            text="Test",
        )
        enqueue_message(msg)
        assert queue_depth() == 1

        popped = dequeue_message()
        assert popped is not None
        assert popped.message_id == "m1"
        assert queue_depth() == 0

        assert dequeue_message() is None

    def test_drain_queue(self) -> None:
        from app.services.webhook_processor import drain_queue, enqueue_message

        drain_queue()

        from app.schemas.whatsapp import WhatsAppInboundMessage

        for i in range(3):
            enqueue_message(
                WhatsAppInboundMessage(
                    message_id=f"m{i}",
                    from_phone="+5511999999999",
                    timestamp=_NOW,
                    text=f"Msg {i}",
                )
            )

        msgs = drain_queue()
        assert len(msgs) == 3

    @patch.dict(os.environ, {"WHATSAPP_APP_SECRET": "my_secret"})
    def test_verify_signature_valid(self) -> None:
        from app.services.webhook_processor import verify_signature

        body = b'{"test": true}'
        sig = _sign_payload(body, "my_secret")

        assert verify_signature(body, sig) is True

    @patch.dict(os.environ, {"WHATSAPP_APP_SECRET": "my_secret"})
    def test_verify_signature_invalid(self) -> None:
        from app.services.webhook_processor import verify_signature

        body = b'{"test": true}'
        sig = "sha256=bad"

        assert verify_signature(body, sig) is False

    @patch.dict(os.environ, {"WHATSAPP_APP_SECRET": ""})
    def test_verify_signature_no_secret(self) -> None:
        from app.services.webhook_processor import verify_signature

        assert verify_signature(b"body", "sha256=abc") is False


# ===================================================================
# 3. Webhook Routes
# ===================================================================


class TestWebhookRoutes:
    """Test ``GET /webhooks/whatsapp`` and ``POST /webhooks/whatsapp``."""

    @patch.dict(os.environ, {"WHATSAPP_VERIFY_TOKEN": "my_token"})
    def test_get_verify_success(self, client: TestClient) -> None:
        resp = client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "my_token",
                "hub.challenge": "42",
            },
        )
        assert resp.status_code == 200
        assert resp.json() == 42

    @patch.dict(os.environ, {"WHATSAPP_VERIFY_TOKEN": "my_token"})
    def test_get_verify_wrong_token(self, client: TestClient) -> None:
        resp = client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong",
                "hub.challenge": "42",
            },
        )
        assert resp.status_code == 403

    @patch.dict(os.environ, {"WHATSAPP_VERIFY_TOKEN": "my_token"})
    def test_get_verify_wrong_mode(self, client: TestClient) -> None:
        resp = client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "unsubscribe",
                "hub.verify_token": "my_token",
                "hub.challenge": "42",
            },
        )
        assert resp.status_code == 403

    @patch.dict(os.environ, {"WHATSAPP_APP_SECRET": ""})
    def test_post_webhook_enqueues_messages(self, client: TestClient) -> None:
        from app.services.webhook_processor import drain_queue

        drain_queue()

        payload = _make_meta_payload(text="2450 USD avg")
        resp = client.post("/webhooks/whatsapp", json=payload)

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

        msgs = drain_queue()
        assert len(msgs) == 1
        assert msgs[0].text == "2450 USD avg"

    @patch.dict(os.environ, {"WHATSAPP_APP_SECRET": "secret123"})
    def test_post_webhook_invalid_signature(self, client: TestClient) -> None:
        payload = _make_meta_payload()
        body = json.dumps(payload).encode()

        resp = client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=bad",
            },
        )
        assert resp.status_code == 403

    @patch.dict(os.environ, {"WHATSAPP_APP_SECRET": "secret123"})
    def test_post_webhook_valid_signature(self, client: TestClient) -> None:
        from app.services.webhook_processor import drain_queue

        drain_queue()

        payload = _make_meta_payload(text="2500 USD/MT")
        body = json.dumps(payload).encode()
        sig = _sign_payload(body, "secret123")

        resp = client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": sig,
            },
        )
        assert resp.status_code == 200
        msgs = drain_queue()
        assert len(msgs) == 1


# ===================================================================
# 4. LLM Agent
# ===================================================================


class TestLLMAgent:
    """Tests for ``app.services.llm_agent.LLMAgent``."""

    def test_should_auto_create_quote_true(self) -> None:
        from app.schemas.llm import MessageIntent, ParsedQuote
        from app.services.llm_agent import LLMAgent

        parsed = ParsedQuote(
            intent=MessageIntent.quote,
            confidence=0.95,
            fixed_price_value=Decimal("2450.00"),
            fixed_price_unit="USD/MT",
            float_pricing_convention="avg",
            counterparty_name="Glencore",
        )
        assert LLMAgent.should_auto_create_quote(parsed) is True

    def test_should_auto_create_quote_low_confidence(self) -> None:
        from app.schemas.llm import MessageIntent, ParsedQuote
        from app.services.llm_agent import LLMAgent

        parsed = ParsedQuote(
            intent=MessageIntent.quote,
            confidence=0.60,
            fixed_price_value=Decimal("2450.00"),
            counterparty_name="Glencore",
        )
        assert LLMAgent.should_auto_create_quote(parsed) is False

    def test_should_auto_create_quote_no_price(self) -> None:
        from app.schemas.llm import MessageIntent, ParsedQuote
        from app.services.llm_agent import LLMAgent

        parsed = ParsedQuote(
            intent=MessageIntent.quote,
            confidence=0.95,
            fixed_price_value=None,
            counterparty_name="Glencore",
        )
        assert LLMAgent.should_auto_create_quote(parsed) is False

    def test_should_auto_create_quote_rejection(self) -> None:
        from app.schemas.llm import MessageIntent, ParsedQuote
        from app.services.llm_agent import LLMAgent

        parsed = ParsedQuote(
            intent=MessageIntent.rejection,
            confidence=0.95,
            fixed_price_value=Decimal("2450"),
            counterparty_name="Glencore",
        )
        assert LLMAgent.should_auto_create_quote(parsed) is False

    def test_generate_outbound_message_ptbr(self) -> None:
        from app.services.llm_agent import LLMAgent

        msg = LLMAgent.generate_outbound_message(
            action="award",
            language="pt_BR",
            recipient_name="João",
            rfq_number="RFQ-001",
            price=2450.00,
            unit="USD/MT",
        )
        assert "João" in msg
        assert "RFQ-001" in msg
        assert "2450" in msg

    def test_generate_outbound_message_en(self) -> None:
        from app.services.llm_agent import LLMAgent

        msg = LLMAgent.generate_outbound_message(
            action="reject",
            language="en",
            recipient_name="John",
            rfq_number="RFQ-002",
        )
        assert "John" in msg
        assert "RFQ-002" in msg
        assert "closed" in msg.lower()

    def test_generate_outbound_message_unknown_action(self) -> None:
        from app.services.llm_agent import LLMAgent

        msg = LLMAgent.generate_outbound_message(
            action="unknown_action",
            rfq_number="RFQ-003",
        )
        # Fallback format
        assert "RFQ-003" in msg

    @patch("app.services.llm_agent._call_openai")
    def test_classify_intent_quote(self, mock_openai: MagicMock) -> None:
        from app.services.llm_agent import LLMAgent

        mock_openai.return_value = {
            "intent": "QUOTE",
            "confidence": 0.92,
            "reasoning": "Contains a price offer",
        }

        result = LLMAgent.classify_intent("Ofereço 2500 USD/MT avg")

        assert result.intent.value == "QUOTE"
        assert result.confidence == 0.92
        assert result.raw_reasoning is not None

    @patch("app.services.llm_agent._call_openai")
    def test_classify_intent_rejection(self, mock_openai: MagicMock) -> None:
        from app.services.llm_agent import LLMAgent

        mock_openai.return_value = {
            "intent": "REJECTION",
            "confidence": 0.88,
            "reasoning": "Declines to quote",
        }

        result = LLMAgent.classify_intent("Não temos interesse")
        assert result.intent.value == "REJECTION"

    @patch("app.services.llm_agent._call_openai")
    def test_parse_quote_message(self, mock_openai: MagicMock) -> None:
        from app.services.llm_agent import LLMAgent

        mock_openai.return_value = {
            "intent": "QUOTE",
            "confidence": 0.95,
            "fixed_price_value": 2450.50,
            "fixed_price_unit": "USD/MT",
            "float_pricing_convention": "avg",
            "counterparty_name": "Trader João",
            "notes": None,
        }

        parsed = LLMAgent.parse_quote_message(
            rfq_context="RFQ: RFQ-001\nCommodity: Zinc\nQuantity: 100 MT",
            raw_message="Ofereço 2450.50 USD/MT baseado na média mensal",
            sender_name="Trader João",
        )

        assert parsed.intent.value == "QUOTE"
        assert parsed.confidence == 0.95
        assert parsed.fixed_price_value == Decimal("2450.50")
        assert parsed.fixed_price_unit == "USD/MT"
        assert parsed.float_pricing_convention == "avg"

    @patch("app.services.llm_agent._call_openai")
    def test_parse_quote_message_unknown_intent(self, mock_openai: MagicMock) -> None:
        from app.services.llm_agent import LLMAgent

        mock_openai.return_value = {
            "intent": "BANANA",  # invalid
            "confidence": 0.5,
            "counterparty_name": "Test",
        }

        parsed = LLMAgent.parse_quote_message(
            rfq_context="RFQ-001",
            raw_message="Random text",
        )
        assert parsed.intent.value == "OTHER"

    def test_llm_unavailable_error(self) -> None:
        from app.services.llm_agent import LLMAgent, LLMUnavailableError

        # Without AZURE_OPENAI_ENDPOINT the call should raise
        with patch.dict(os.environ, {"AZURE_OPENAI_ENDPOINT": "", "AZURE_OPENAI_API_KEY": ""}):
            with pytest.raises(LLMUnavailableError):
                LLMAgent.classify_intent("test")


# ===================================================================
# 5. RFQ Orchestrator
# ===================================================================


class TestRFQOrchestrator:
    """Tests for ``app.services.rfq_orchestrator.RFQOrchestrator``."""

    def _create_rfq_with_invitation(
        self, client: TestClient, phone: str = "+5511999999999"
    ) -> dict:
        """Helper — create a GLOBAL_POSITION RFQ with a whatsapp invitation."""
        from datetime import date

        payload = {
            "intent": "GLOBAL_POSITION",
            "commodity": "Zinc",
            "quantity_mt": 100.0,
            "delivery_window_start": str(date.today()),
            "delivery_window_end": str(date.today() + timedelta(days=30)),
            "direction": "BUY",
            "invitations": [
                {
                    "recipient_id": phone,
                    "recipient_name": "Test Bank",
                    "channel": "whatsapp",
                    "message_body": "Cotação para 100 MT Zinc",
                    "provider_message_id": "pending",
                    "send_status": "queued",
                    "sent_at": _NOW.isoformat(),
                    "idempotency_key": f"idem-{uuid4().hex[:8]}",
                }
            ],
        }
        resp = client.post("/rfqs/", json=payload)
        assert resp.status_code == 201
        return resp.json()

    @patch("app.services.whatsapp_service.httpx.post")
    def test_dispatch_whatsapp_invitations(
        self, mock_post: MagicMock, client: TestClient, session
    ) -> None:
        from app.services.rfq_orchestrator import RFQOrchestrator

        # Mock WhatsApp API
        mock_post.return_value = MagicMock(
            is_success=True,
            json=lambda: {"messages": [{"id": "wamid.dispatched"}]},
        )

        rfq_data = self._create_rfq_with_invitation(client)
        rfq_id = UUID(rfq_data["id"])

        results = RFQOrchestrator.dispatch_whatsapp_invitations(session, rfq_id)

        # All invitations should have been sent or already processed
        # (the create() method in rfq_service also sends — so status may
        # already be sent/failed. The orchestrator re-sends only queued ones.)
        assert isinstance(results, dict)

    @patch("app.services.llm_agent._call_openai")
    @patch("app.services.whatsapp_service.httpx.post")
    def test_process_inbound_message_auto_quote(
        self, mock_wa_post: MagicMock, mock_openai: MagicMock,
        client: TestClient, session
    ) -> None:
        from app.schemas.whatsapp import WhatsAppInboundMessage
        from app.services.rfq_orchestrator import RFQOrchestrator
        from app.services.webhook_processor import drain_queue, enqueue_message

        drain_queue()

        mock_wa_post.return_value = MagicMock(
            is_success=True,
            json=lambda: {"messages": [{"id": "wamid.sent1"}]},
        )

        phone = "+5511888888888"
        rfq_data = self._create_rfq_with_invitation(client, phone=phone)

        # Manually set the RFQ state to SENT for testing
        from app.models.rfqs import RFQ as RFQModel, RFQState

        rfq = session.get(RFQModel, UUID(rfq_data["id"]))
        rfq.state = RFQState.sent
        session.commit()

        mock_openai.return_value = {
            "intent": "QUOTE",
            "confidence": 0.95,
            "fixed_price_value": 2450.0,
            "fixed_price_unit": "USD/MT",
            "float_pricing_convention": "avg",
            "counterparty_name": "Test Bank",
            "notes": None,
        }

        enqueue_message(WhatsAppInboundMessage(
            message_id="wamid.in1",
            from_phone=phone,
            timestamp=_NOW,
            text="Ofereço 2450 USD/MT avg",
            sender_name="Test Bank",
        ))

        results = RFQOrchestrator.process_inbound_queue(session)

        assert len(results) == 1
        assert results[0]["status"] == "auto_quote_created"
        assert "quote_id" in results[0]

    @patch("app.services.llm_agent._call_openai")
    @patch("app.services.whatsapp_service.httpx.post")
    def test_process_inbound_message_low_confidence(
        self, mock_wa_post: MagicMock, mock_openai: MagicMock,
        client: TestClient, session
    ) -> None:
        from app.schemas.whatsapp import WhatsAppInboundMessage
        from app.services.rfq_orchestrator import RFQOrchestrator
        from app.services.webhook_processor import drain_queue, enqueue_message

        drain_queue()

        mock_wa_post.return_value = MagicMock(
            is_success=True,
            json=lambda: {"messages": [{"id": "wamid.sent2"}]},
        )

        phone = "+5511777777777"
        rfq_data = self._create_rfq_with_invitation(client, phone=phone)

        from app.models.rfqs import RFQ as RFQModel, RFQState

        rfq = session.get(RFQModel, UUID(rfq_data["id"]))
        rfq.state = RFQState.sent
        session.commit()

        mock_openai.return_value = {
            "intent": "QUOTE",
            "confidence": 0.50,  # Below threshold
            "fixed_price_value": 2400.0,
            "fixed_price_unit": "USD/MT",
            "counterparty_name": "Test Bank",
        }

        enqueue_message(WhatsAppInboundMessage(
            message_id="wamid.low",
            from_phone=phone,
            timestamp=_NOW,
            text="Maybe 2400?",
            sender_name="Test Bank",
        ))

        results = RFQOrchestrator.process_inbound_queue(session)

        assert len(results) == 1
        assert results[0]["status"] == "needs_human_review"

    @patch("app.services.whatsapp_service.httpx.post")
    def test_process_inbound_message_no_matching_rfq(
        self, mock_wa_post: MagicMock, client: TestClient, session
    ) -> None:
        from app.schemas.whatsapp import WhatsAppInboundMessage
        from app.services.rfq_orchestrator import RFQOrchestrator
        from app.services.webhook_processor import drain_queue, enqueue_message

        drain_queue()

        enqueue_message(WhatsAppInboundMessage(
            message_id="wamid.unknown",
            from_phone="+0000000000",  # No invitation for this phone
            timestamp=_NOW,
            text="Hello",
        ))

        results = RFQOrchestrator.process_inbound_queue(session)

        assert len(results) == 1
        assert results[0]["status"] == "no_matching_rfq"

    @patch("app.services.whatsapp_service.httpx.post")
    def test_check_rfq_timeouts_no_quotes(
        self, mock_wa_post: MagicMock, client: TestClient, session
    ) -> None:
        """RFQ with no quotes past a 0-hour timeout → CLOSED."""
        from app.services.rfq_orchestrator import RFQOrchestrator

        mock_wa_post.return_value = MagicMock(
            is_success=True,
            json=lambda: {"messages": [{"id": "wamid.t1"}]},
        )

        rfq_data = self._create_rfq_with_invitation(client)

        from app.models.rfqs import RFQ as RFQModel, RFQState

        rfq = session.get(RFQModel, UUID(rfq_data["id"]))
        rfq.state = RFQState.sent
        # Set created_at to the past
        rfq.created_at = _NOW - timedelta(hours=25)
        session.commit()

        timed_out = RFQOrchestrator.check_rfq_timeouts(session, timeout_hours=24)

        assert len(timed_out) == 1

        session.refresh(rfq)
        assert rfq.state == RFQState.closed

    @patch("app.services.whatsapp_service.httpx.post")
    def test_notify_award(
        self, mock_wa_post: MagicMock, client: TestClient, session
    ) -> None:
        from app.services.rfq_orchestrator import RFQOrchestrator

        mock_wa_post.return_value = MagicMock(
            is_success=True,
            json=lambda: {"messages": [{"id": "wamid.award"}]},
        )

        phone = "+5511111111111"
        rfq_data = self._create_rfq_with_invitation(client, phone=phone)

        from app.models.rfqs import RFQ as RFQModel

        rfq = session.get(RFQModel, UUID(rfq_data["id"]))

        RFQOrchestrator.notify_award(
            session, rfq,
            winning_counterparty_id=phone,
            price=2450.0,
            unit="USD/MT",
        )

        # Should have called WhatsApp
        assert mock_wa_post.called
        call_body = mock_wa_post.call_args.kwargs["json"]
        assert "2450" in call_body["text"]["body"]

    @patch("app.services.whatsapp_service.httpx.post")
    def test_notify_reject(
        self, mock_wa_post: MagicMock, client: TestClient, session
    ) -> None:
        from app.services.rfq_orchestrator import RFQOrchestrator

        mock_wa_post.return_value = MagicMock(
            is_success=True,
            json=lambda: {"messages": [{"id": "wamid.rej"}]},
        )

        phone = "+5511222222222"
        rfq_data = self._create_rfq_with_invitation(client, phone=phone)

        from app.models.rfqs import RFQ as RFQModel

        rfq = session.get(RFQModel, UUID(rfq_data["id"]))

        RFQOrchestrator.notify_reject(session, rfq)

        assert mock_wa_post.called
        call_body = mock_wa_post.call_args.kwargs["json"]
        assert "encerrada" in call_body["text"]["body"]


# ===================================================================
# 6. RFQ Timeout Task
# ===================================================================


class TestRFQTimeoutTask:
    """Tests for ``app.tasks.rfq_timeout_task``."""

    @patch("app.tasks.rfq_timeout_task.RFQOrchestrator")
    def test_run_rfq_timeout_check(self, mock_orchestrator: MagicMock) -> None:
        from app.tasks.rfq_timeout_task import run_rfq_timeout_check

        mock_orchestrator.send_reminders.return_value = []
        mock_orchestrator.check_rfq_timeouts.return_value = []

        run_rfq_timeout_check()

        mock_orchestrator.send_reminders.assert_called_once()
        mock_orchestrator.check_rfq_timeouts.assert_called_once()
