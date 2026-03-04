"""WhatsApp provider abstraction layer.

Supports multiple backends for outbound WhatsApp messaging:

- ``meta``  — Direct Meta Cloud API (default)
- ``twilio`` — Twilio WhatsApp API
- ``fake`` / ``mock`` / ``test`` — No-op provider for testing

The active provider is selected via the ``WHATSAPP_PROVIDER`` environment
variable.  All providers implement :class:`WhatsAppProviderBase` and return
:class:`WhatsAppSendResult`.
"""

from __future__ import annotations

import abc
import os
from typing import Any

import httpx

from app.core.logging import get_logger
from app.schemas.whatsapp import WhatsAppSendResult

logger = get_logger()


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class WhatsAppProviderBase(abc.ABC):
    """Interface that every WhatsApp provider must implement."""

    @abc.abstractmethod
    def send_text_message(self, phone: str, text: str) -> WhatsAppSendResult:
        """Send a free-form text message."""

    @abc.abstractmethod
    def send_template_message(
        self,
        phone: str,
        template_name: str,
        params: list[str] | None = None,
        language_code: str = "pt_BR",
    ) -> WhatsAppSendResult:
        """Send a pre-approved template message."""


# ---------------------------------------------------------------------------
# Fake / test provider
# ---------------------------------------------------------------------------


class FakeWhatsAppProvider(WhatsAppProviderBase):
    """No-op provider that logs calls but never makes HTTP requests."""

    def send_text_message(self, phone: str, text: str) -> WhatsAppSendResult:
        logger.info("whatsapp_fake_send", to=phone, msg_type="text")
        return WhatsAppSendResult(
            success=True,
            provider_message_id=f"fake-{phone}",
        )

    def send_template_message(
        self,
        phone: str,
        template_name: str,
        params: list[str] | None = None,
        language_code: str = "pt_BR",
    ) -> WhatsAppSendResult:
        logger.info(
            "whatsapp_fake_send",
            to=phone,
            msg_type="template",
            template=template_name,
        )
        return WhatsAppSendResult(
            success=True,
            provider_message_id=f"fake-{phone}",
        )


# ---------------------------------------------------------------------------
# Meta Cloud API provider (original implementation)
# ---------------------------------------------------------------------------

_DEFAULT_META_API_URL = "https://graph.facebook.com/v21.0"


class MetaWhatsAppProvider(WhatsAppProviderBase):
    """Direct integration with Meta's WhatsApp Business Cloud API."""

    def _api_url(self) -> str:
        return os.getenv("WHATSAPP_API_URL", _DEFAULT_META_API_URL).rstrip("/")

    def _access_token(self) -> str:
        token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        if not token:
            raise ValueError(
                "WHATSAPP_ACCESS_TOKEN not configured — cannot send WhatsApp messages"
            )
        return token

    def _phone_number_id(self) -> str:
        return os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    def _build_url(self) -> str:
        return f"{self._api_url()}/{self._phone_number_id()}/messages"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token()}",
            "Content-Type": "application/json",
        }

    def send_text_message(self, phone: str, text: str) -> WhatsAppSendResult:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text},
        }
        return self._send(payload)

    def send_template_message(
        self,
        phone: str,
        template_name: str,
        params: list[str] | None = None,
        language_code: str = "pt_BR",
    ) -> WhatsAppSendResult:
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
        return self._send(payload)

    def _send(self, payload: dict[str, Any]) -> WhatsAppSendResult:
        url = self._build_url()
        headers = self._headers()

        logger.info(
            "whatsapp_send_attempt",
            provider="meta",
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
                    provider="meta",
                    to=payload.get("to"),
                    provider_message_id=msg_id,
                )
                return WhatsAppSendResult(success=True, provider_message_id=msg_id)

            error = data.get("error", {})
            logger.error(
                "whatsapp_send_api_error",
                provider="meta",
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
            logger.error("whatsapp_send_timeout", provider="meta", to=payload.get("to"))
            return WhatsAppSendResult(
                success=False,
                error_code="TIMEOUT",
                error_message="Request timed out",
            )
        except Exception as exc:
            logger.error(
                "whatsapp_send_exception",
                provider="meta",
                to=payload.get("to"),
                error=str(exc),
                exc_info=True,
            )
            return WhatsAppSendResult(
                success=False,
                error_code="INTERNAL",
                error_message=str(exc)[:500],
            )


# ---------------------------------------------------------------------------
# Twilio WhatsApp provider
# ---------------------------------------------------------------------------


class TwilioWhatsAppProvider(WhatsAppProviderBase):
    """WhatsApp messaging via the Twilio API.

    Environment variables:

    - ``TWILIO_ACCOUNT_SID``   — Twilio Account SID
    - ``TWILIO_AUTH_TOKEN``     — Twilio Auth Token
    - ``TWILIO_WHATSAPP_FROM`` — Sender number in format ``whatsapp:+14155238886``

    Twilio's REST API endpoint:
    ``POST https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json``
    """

    def _account_sid(self) -> str:
        sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        if not sid:
            raise ValueError("TWILIO_ACCOUNT_SID not configured")
        return sid

    def _auth_token(self) -> str:
        token = os.getenv("TWILIO_AUTH_TOKEN", "")
        if not token:
            raise ValueError("TWILIO_AUTH_TOKEN not configured")
        return token

    def _from_number(self) -> str:
        """Return the sender number in Twilio format ``whatsapp:+NNNNN``."""
        num = os.getenv("TWILIO_WHATSAPP_FROM", "")
        if not num:
            raise ValueError("TWILIO_WHATSAPP_FROM not configured")
        if not num.startswith("whatsapp:"):
            num = f"whatsapp:{num}"
        return num

    def _build_url(self) -> str:
        return (
            f"https://api.twilio.com/2010-04-01"
            f"/Accounts/{self._account_sid()}/Messages.json"
        )

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Ensure phone is in Twilio ``whatsapp:+NNNNN`` format."""
        phone = phone.strip()
        if phone.startswith("whatsapp:"):
            return phone
        return f"whatsapp:{phone}"

    def send_text_message(self, phone: str, text: str) -> WhatsAppSendResult:
        return self._send(phone=phone, body=text)

    def send_template_message(
        self,
        phone: str,
        template_name: str,
        params: list[str] | None = None,
        language_code: str = "pt_BR",
    ) -> WhatsAppSendResult:
        # Twilio uses Content Templates via ContentSid, but also accepts
        # the simpler approach of sending the rendered body directly.
        # For now we send variable-substituted text.  If you have a
        # Twilio Content Template SID, set TWILIO_CONTENT_SID_<TEMPLATE_NAME>.
        content_sid = os.getenv(f"TWILIO_CONTENT_SID_{template_name.upper()}", "")

        if content_sid:
            # Use Twilio Content API
            variables = {}
            if params:
                variables = {str(i + 1): p for i, p in enumerate(params)}
            return self._send(
                phone=phone,
                content_sid=content_sid,
                content_variables=variables,
            )

        # Fallback: send as plain text (template body must be rendered
        # by the caller — e.g. RFQ orchestrator already builds the text).
        body = f"[{template_name}]"
        if params:
            body += " " + " | ".join(params)
        logger.warning(
            "twilio_template_fallback_to_text",
            template_name=template_name,
            hint="Set TWILIO_CONTENT_SID_<NAME> for Content Templates",
        )
        return self._send(phone=phone, body=body)

    def _send(
        self,
        phone: str,
        body: str | None = None,
        content_sid: str | None = None,
        content_variables: dict | None = None,
    ) -> WhatsAppSendResult:
        """Execute the HTTP POST to Twilio Messages API."""
        to_number = self._normalize_phone(phone)

        try:
            url = self._build_url()
            from_number = self._from_number()
        except ValueError as exc:
            logger.error(
                "whatsapp_send_config_error",
                provider="twilio",
                to=to_number,
                error=str(exc),
            )
            return WhatsAppSendResult(
                success=False,
                error_code="CONFIG",
                error_message=str(exc),
            )

        data: dict[str, str] = {
            "From": from_number,
            "To": to_number,
        }
        if content_sid:
            data["ContentSid"] = content_sid
            if content_variables:
                import json

                data["ContentVariables"] = json.dumps(content_variables)
        elif body:
            data["Body"] = body
        else:
            return WhatsAppSendResult(
                success=False,
                error_code="NO_BODY",
                error_message="No message body or content SID provided",
            )

        logger.info(
            "whatsapp_send_attempt",
            provider="twilio",
            to=to_number,
            msg_type="content_template" if content_sid else "text",
        )

        try:
            response = httpx.post(
                url,
                data=data,
                auth=(self._account_sid(), self._auth_token()),
                timeout=15.0,
            )
            resp_json = response.json()

            if response.status_code in (200, 201):
                msg_sid = resp_json.get("sid", "")
                logger.info(
                    "whatsapp_send_success",
                    provider="twilio",
                    to=to_number,
                    provider_message_id=msg_sid,
                    twilio_status=resp_json.get("status"),
                )
                return WhatsAppSendResult(
                    success=True,
                    provider_message_id=msg_sid,
                )

            error_code = str(resp_json.get("code", response.status_code))
            error_msg = resp_json.get("message", "Unknown Twilio error")
            logger.error(
                "whatsapp_send_api_error",
                provider="twilio",
                to=to_number,
                status=response.status_code,
                error_code=error_code,
                error_message=error_msg,
            )
            return WhatsAppSendResult(
                success=False,
                error_code=error_code,
                error_message=error_msg,
            )

        except httpx.TimeoutException:
            logger.error("whatsapp_send_timeout", provider="twilio", to=to_number)
            return WhatsAppSendResult(
                success=False,
                error_code="TIMEOUT",
                error_message="Request timed out",
            )
        except Exception as exc:
            logger.error(
                "whatsapp_send_exception",
                provider="twilio",
                to=to_number,
                error=str(exc),
                exc_info=True,
            )
            return WhatsAppSendResult(
                success=False,
                error_code="INTERNAL",
                error_message=str(exc)[:500],
            )


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, type[WhatsAppProviderBase]] = {
    "meta": MetaWhatsAppProvider,
    "twilio": TwilioWhatsAppProvider,
    "fake": FakeWhatsAppProvider,
    "mock": FakeWhatsAppProvider,
    "test": FakeWhatsAppProvider,
}


def get_provider_name() -> str:
    """Return the canonical provider name from ``WHATSAPP_PROVIDER``."""
    raw = os.getenv("WHATSAPP_PROVIDER", "meta").lower().strip()
    if raw in _PROVIDERS:
        return raw
    logger.warning("whatsapp_unknown_provider", raw=raw, fallback="meta")
    return "meta"


def get_provider() -> WhatsAppProviderBase:
    """Return an instance of the configured WhatsApp provider."""
    name = get_provider_name()
    return _PROVIDERS[name]()
