"""WhatsApp Cloud API service for outbound messaging.

Integrates with Meta's WhatsApp Business Cloud API to send template and text
messages.  Configuration is via environment variables:

- ``WHATSAPP_API_URL`` — base URL (default: https://graph.facebook.com/v19.0)
- ``WHATSAPP_ACCESS_TOKEN`` — permanent access token
- ``WHATSAPP_PHONE_NUMBER_ID`` — sender phone-number ID

All outbound calls use :pymod:`httpx` with a configurable timeout and structured
logging for observability.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from app.core.logging import get_logger
from app.schemas.whatsapp import WhatsAppSendResult

logger = get_logger()

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

_DEFAULT_API_URL = "https://graph.facebook.com/v19.0"


def _api_url() -> str:
    return os.getenv("WHATSAPP_API_URL", _DEFAULT_API_URL).rstrip("/")


def _access_token() -> str:
    token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    if not token:
        logger.warning("whatsapp_access_token_missing")
    return token


def _phone_number_id() -> str:
    return os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class WhatsAppService:
    """Thin wrapper around the WhatsApp Cloud API."""

    @staticmethod
    def _build_url() -> str:
        return f"{_api_url()}/{_phone_number_id()}/messages"

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "Authorization": f"Bearer {_access_token()}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def send_template_message(
        phone: str,
        template_name: str,
        params: list[str] | None = None,
        language_code: str = "pt_BR",
    ) -> WhatsAppSendResult:
        """Send a pre-approved WhatsApp template message.

        Parameters
        ----------
        phone:
            Recipient phone number in E.164 format (e.g. ``+5511999999999``).
        template_name:
            Name of the approved template on Meta Business.
        params:
            Positional parameters to inject into the template body.
        language_code:
            BCP-47 language code for the template (default ``pt_BR``).
        """
        components: list[dict[str, Any]] = []
        if params:
            components.append(
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in params],
                }
            )

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
            },
        }
        return WhatsAppService._send(payload)

    @staticmethod
    def send_text_message(phone: str, text: str) -> WhatsAppSendResult:
        """Send a free-form text message via WhatsApp.

        Parameters
        ----------
        phone:
            Recipient phone number in E.164 format.
        text:
            Message body (max 4096 chars per WhatsApp limits).
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text},
        }
        return WhatsAppService._send(payload)

    @staticmethod
    def _send(payload: dict[str, Any]) -> WhatsAppSendResult:
        """Execute the HTTP call to the WhatsApp Cloud API."""
        url = WhatsAppService._build_url()
        headers = WhatsAppService._headers()

        logger.info(
            "whatsapp_send_attempt",
            to=payload.get("to"),
            msg_type=payload.get("type"),
        )

        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=15.0)
            data = response.json()

            if response.is_success:
                msg_id = ""
                messages = data.get("messages", [])
                if messages:
                    msg_id = messages[0].get("id", "")
                logger.info(
                    "whatsapp_send_success",
                    to=payload.get("to"),
                    provider_message_id=msg_id,
                )
                return WhatsAppSendResult(
                    success=True,
                    provider_message_id=msg_id,
                )

            # API returned an error
            error = data.get("error", {})
            logger.error(
                "whatsapp_send_api_error",
                to=payload.get("to"),
                status=response.status_code,
                error_code=str(error.get("code", "")),
                error_message=error.get("message", ""),
            )
            return WhatsAppSendResult(
                success=False,
                error_code=str(error.get("code", "")),
                error_message=error.get("message", "Unknown API error"),
            )

        except httpx.TimeoutException:
            logger.error("whatsapp_send_timeout", to=payload.get("to"))
            return WhatsAppSendResult(
                success=False,
                error_code="TIMEOUT",
                error_message="Request timed out",
            )
        except Exception as exc:
            logger.error(
                "whatsapp_send_exception",
                to=payload.get("to"),
                error=str(exc),
                exc_info=True,
            )
            return WhatsAppSendResult(
                success=False,
                error_code="INTERNAL",
                error_message=str(exc)[:500],
            )
