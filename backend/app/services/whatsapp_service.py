"""WhatsApp outbound messaging service — provider-agnostic facade.

Delegates to the configured provider backend:

- ``meta``   — Direct Meta WhatsApp Business Cloud API  (default)
- ``twilio`` — Twilio WhatsApp API
- ``fake`` / ``mock`` / ``test`` — No-op for testing

The provider is selected via ``WHATSAPP_PROVIDER`` env var.

Legacy helper functions (``_api_url``, ``_access_token``, ``_phone_number_id``)
are preserved for backward compatibility with existing tests.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from app.core.logging import get_logger
from app.schemas.whatsapp import WhatsAppSendResult
from app.services.whatsapp_providers import (
    WhatsAppProviderBase,
    get_provider,
    get_provider_name,
)

logger = get_logger()

# ---------------------------------------------------------------------------
# Legacy configuration helpers — kept for backward-compat with existing tests
# ---------------------------------------------------------------------------

_DEFAULT_API_URL = "https://graph.facebook.com/v21.0"


def _is_fake_provider() -> bool:
    """Return True when running with the fake/mock WhatsApp provider."""
    return get_provider_name() in ("fake", "mock", "test")


def _api_url() -> str:
    return os.getenv("WHATSAPP_API_URL", _DEFAULT_API_URL).rstrip("/")


def _access_token() -> str:
    token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    if not token:
        raise ValueError(
            "WHATSAPP_ACCESS_TOKEN not configured — cannot send WhatsApp messages"
        )
    return token


def _phone_number_id() -> str:
    return os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")


# ---------------------------------------------------------------------------
# Public API — facade delegating to the active provider
# ---------------------------------------------------------------------------


class WhatsAppService:
    """Provider-agnostic facade for outbound WhatsApp messaging.

    All callers continue to use ``WhatsAppService.send_text_message(...)``
    etc.  The underlying provider (Meta / Twilio / Fake) is resolved at
    call time from ``WHATSAPP_PROVIDER``.
    """

    @staticmethod
    def _get_provider() -> WhatsAppProviderBase:
        return get_provider()

    # --- kept for backward compat (used only by Meta provider tests) ---

    @staticmethod
    def _build_url() -> str:
        return f"{_api_url()}/{_phone_number_id()}/messages"

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "Authorization": f"Bearer {_access_token()}",
            "Content-Type": "application/json",
        }

    # --- public methods (unchanged signatures) ---

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
            Name of the approved template.
        params:
            Positional parameters to inject into the template body.
        language_code:
            BCP-47 language code for the template (default ``pt_BR``).
        """
        provider = WhatsAppService._get_provider()
        return provider.send_template_message(
            phone=phone,
            template_name=template_name,
            params=params,
            language_code=language_code,
        )

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
        provider = WhatsAppService._get_provider()
        return provider.send_text_message(phone=phone, text=text)
