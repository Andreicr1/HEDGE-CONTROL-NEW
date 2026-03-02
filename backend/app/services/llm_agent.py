"""LLM Agent for parsing inbound counterparty messages into structured quotes.

Integrates with Azure OpenAI (GPT-4o-mini) to:
1. Classify message intent (QUOTE / REJECTION / QUESTION / OTHER).
2. Extract structured quote data when intent is QUOTE.
3. Generate outbound messages for different RFQ lifecycle events.

Configuration via environment variables:
- ``AZURE_OPENAI_ENDPOINT``
- ``AZURE_OPENAI_API_KEY``
- ``AZURE_OPENAI_DEPLOYMENT`` (default: ``gpt-4o-mini``)

The agent is designed to be cost-efficient (< $0.001 per call with GPT-4o-mini)
and includes a confidence threshold (0.85) for automatic processing.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.core.logging import get_logger
from app.schemas.llm import LLMClassifyResult, MessageIntent, ParsedQuote

logger = get_logger()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFIDENCE_THRESHOLD = 0.85

_CLASSIFY_SYSTEM_PROMPT = """You are an expert commodity trading assistant.
Classify the following message from a counterparty responding to an RFQ
(Request for Quote) into one of these intents:
- QUOTE: The message contains a price offer / quotation
- REJECTION: The counterparty declines to quote
- QUESTION: The counterparty is asking for clarification
- OTHER: Anything else (greeting, acknowledgment, etc.)

Respond ONLY with a JSON object: {"intent": "...", "confidence": 0.0-1.0, "reasoning": "..."}
"""

_PARSE_SYSTEM_PROMPT = """You are an expert commodity trading assistant.
Extract the structured quote information from the following message.
The RFQ context is provided so you understand what is being quoted.

Respond ONLY with a JSON object:
{
  "intent": "QUOTE",
  "confidence": 0.0-1.0,
  "fixed_price_value": <number or null>,
  "fixed_price_unit": "<string like USD/MT or null>",
  "float_pricing_convention": "<avg|avginter|c2r or null>",
  "counterparty_name": "<name>",
  "notes": "<any additional notes or null>"
}

If you cannot reliably parse the quote, set confidence below 0.85.
Support both Portuguese (PT-BR) and English messages.
"""

_GENERATE_TEMPLATES = {
    "rfq_request": (
        "Prezado(a) {recipient_name},\n\n"
        "Solicitamos cotação para:\n"
        "- Commodity: {commodity}\n"
        "- Quantidade: {quantity_mt} MT\n"
        "- Janela de entrega: {delivery_start} a {delivery_end}\n"
        "- Direção: {direction}\n"
        "- Referência: {rfq_number}\n\n"
        "Favor enviar sua cotação até {deadline}.\n"
        "Atenciosamente."
    ),
    "rfq_request_en": (
        "Dear {recipient_name},\n\n"
        "We request a quote for:\n"
        "- Commodity: {commodity}\n"
        "- Quantity: {quantity_mt} MT\n"
        "- Delivery window: {delivery_start} to {delivery_end}\n"
        "- Direction: {direction}\n"
        "- Reference: {rfq_number}\n\n"
        "Please submit your quote by {deadline}.\n"
        "Best regards."
    ),
    "refresh": (
        "Prezado(a) {recipient_name},\n\n"
        "Solicitamos a renovação da sua cotação para a RFQ {rfq_number}.\n"
        "Favor reenviar sua proposta atualizada.\n"
        "Atenciosamente."
    ),
    "refresh_en": (
        "Dear {recipient_name},\n\n"
        "Please resubmit your updated quote for RFQ {rfq_number}.\n"
        "Best regards."
    ),
    "award": (
        "Prezado(a) {recipient_name},\n\n"
        "Temos o prazer de informar que sua cotação de {price} {unit} "
        "foi aceita para a RFQ {rfq_number}.\n"
        "Entraremos em contato para formalização do contrato.\n"
        "Atenciosamente."
    ),
    "award_en": (
        "Dear {recipient_name},\n\n"
        "We are pleased to inform you that your quote of {price} {unit} "
        "has been accepted for RFQ {rfq_number}.\n"
        "We will contact you for contract formalization.\n"
        "Best regards."
    ),
    "reject": (
        "Prezado(a) {recipient_name},\n\n"
        "Informamos que a RFQ {rfq_number} foi encerrada.\n"
        "Agradecemos sua participação.\n"
        "Atenciosamente."
    ),
    "reject_en": (
        "Dear {recipient_name},\n\n"
        "We inform you that RFQ {rfq_number} has been closed.\n"
        "Thank you for your participation.\n"
        "Best regards."
    ),
}


# ---------------------------------------------------------------------------
# Azure OpenAI client helpers
# ---------------------------------------------------------------------------


def _get_endpoint() -> str:
    return os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")


def _get_api_key() -> str:
    return os.getenv("AZURE_OPENAI_API_KEY", "")


def _get_deployment() -> str:
    return os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")


def _call_openai(
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    """Call Azure OpenAI chat completions and return the parsed JSON response.

    Raises ``LLMUnavailableError`` if the call fails.
    """
    endpoint = _get_endpoint()
    api_key = _get_api_key()
    deployment = _get_deployment()

    if not endpoint or not api_key:
        raise LLMUnavailableError("Azure OpenAI not configured")

    url = (
        f"{endpoint}/openai/deployments/{deployment}"
        f"/chat/completions?api-version=2024-02-01"
    )
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 500,
        "response_format": {"type": "json_object"},
    }

    try:
        resp = httpx.post(url, json=body, headers=headers, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except httpx.TimeoutException:
        logger.error("llm_timeout")
        raise LLMUnavailableError("Azure OpenAI request timed out")
    except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
        logger.error("llm_call_failed", error=str(exc), exc_info=True)
        raise LLMUnavailableError(f"Azure OpenAI call failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class LLMUnavailableError(Exception):
    """Raised when the LLM backend is not reachable or not configured."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class LLMAgent:
    """Stateless LLM-powered agent for RFQ message processing."""

    @staticmethod
    def classify_intent(message: str) -> LLMClassifyResult:
        """Classify a raw message into an intent category.

        Returns a :class:`LLMClassifyResult` with intent, confidence, and
        optional reasoning.
        """
        result = _call_openai(_CLASSIFY_SYSTEM_PROMPT, message)

        intent_str = result.get("intent", "OTHER").upper()
        try:
            intent = MessageIntent(intent_str)
        except ValueError:
            intent = MessageIntent.other

        confidence = float(result.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        return LLMClassifyResult(
            intent=intent,
            confidence=confidence,
            raw_reasoning=result.get("reasoning"),
        )

    @staticmethod
    def parse_quote_message(
        rfq_context: str,
        raw_message: str,
        sender_name: str = "Unknown",
    ) -> ParsedQuote:
        """Parse a raw counterparty message into a structured quote.

        Parameters
        ----------
        rfq_context:
            A textual description of the RFQ being quoted (commodity, qty, etc.).
        raw_message:
            The raw text message received from the counterparty.
        sender_name:
            Name of the counterparty sending the message.
        """
        user_prompt = (
            f"RFQ Context:\n{rfq_context}\n\n"
            f"Counterparty: {sender_name}\n\n"
            f"Message:\n{raw_message}"
        )
        result = _call_openai(_PARSE_SYSTEM_PROMPT, user_prompt)

        intent_str = result.get("intent", "OTHER").upper()
        try:
            intent = MessageIntent(intent_str)
        except ValueError:
            intent = MessageIntent.other

        confidence = float(result.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        fixed_price_value = None
        raw_price = result.get("fixed_price_value")
        if raw_price is not None:
            try:
                fixed_price_value = Decimal(str(raw_price))
            except (InvalidOperation, ValueError):
                fixed_price_value = None

        return ParsedQuote(
            intent=intent,
            confidence=confidence,
            fixed_price_value=fixed_price_value,
            fixed_price_unit=result.get("fixed_price_unit"),
            float_pricing_convention=result.get("float_pricing_convention"),
            counterparty_name=result.get("counterparty_name", sender_name),
            notes=result.get("notes"),
        )

    @staticmethod
    def generate_outbound_message(
        action: str,
        language: str = "pt_BR",
        **kwargs: Any,
    ) -> str:
        """Generate a contextual outbound message using templates.

        Parameters
        ----------
        action:
            One of ``rfq_request``, ``refresh``, ``award``, ``reject``.
        language:
            ``pt_BR`` (default) or ``en``.
        **kwargs:
            Template variables (e.g. ``recipient_name``, ``commodity``,
            ``rfq_number``, etc.).
        """
        template_key = action if language == "pt_BR" else f"{action}_en"
        template = _GENERATE_TEMPLATES.get(template_key)

        if not template:
            logger.warning(
                "llm_template_not_found",
                action=action,
                language=language,
            )
            # Fallback to Portuguese
            template = _GENERATE_TEMPLATES.get(action, "")

        if not template:
            return f"[{action}] {kwargs.get('rfq_number', 'N/A')}"

        try:
            return template.format(**kwargs)
        except KeyError as exc:
            logger.warning(
                "llm_template_missing_var",
                action=action,
                missing_key=str(exc),
            )
            return template

    @staticmethod
    def should_auto_create_quote(parsed: ParsedQuote) -> bool:
        """Return ``True`` if the parsed quote has high enough confidence
        for automatic quote creation (>= 0.85 threshold)."""
        return (
            parsed.intent == MessageIntent.quote
            and parsed.confidence >= CONFIDENCE_THRESHOLD
            and parsed.fixed_price_value is not None
        )
