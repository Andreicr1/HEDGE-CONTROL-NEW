"""Unit tests for WhatsApp outbound messaging — Meta & Twilio providers."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

pytestmark = pytest.mark.no_mock_whatsapp

from app.services.whatsapp_service import (
    WhatsAppService,
    _access_token,
    _api_url,
    _phone_number_id,
)
from app.services.whatsapp_providers import (
    MetaWhatsAppProvider,
    TwilioWhatsAppProvider,
    FakeWhatsAppProvider,
    get_provider,
    get_provider_name,
)


# ── helpers ──────────────────────────────────────────────────────────────

_ENV_META = {
    "WHATSAPP_ACCESS_TOKEN": "test-token",
    "WHATSAPP_PHONE_NUMBER_ID": "123456",
    "WHATSAPP_API_URL": "https://api.example.com",
    "WHATSAPP_PROVIDER": "meta",
}

_ENV_TWILIO = {
    "TWILIO_ACCOUNT_SID": "ACtest123",
    "TWILIO_AUTH_TOKEN": "test-auth-token",
    "TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886",
    "WHATSAPP_PROVIDER": "twilio",
}

# Backward compat alias
_ENV = _ENV_META


def _success_response(msg_id: str = "wamid.abc123") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.is_success = True
    resp.status_code = 200
    resp.json.return_value = {"messages": [{"id": msg_id}]}
    return resp


def _error_response(
    status: int = 400, code: int = 131030, message: str = "Rate limit hit"
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.is_success = False
    resp.status_code = status
    resp.json.return_value = {"error": {"code": code, "message": message}}
    return resp


def _twilio_success_response(sid: str = "SM1234567890") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 201
    resp.json.return_value = {"sid": sid, "status": "queued"}
    return resp


def _twilio_error_response(
    status: int = 400, code: int = 21211, message: str = "Invalid phone"
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json.return_value = {"code": code, "message": message}
    return resp


# ── config helpers ───────────────────────────────────────────────────────


def test_access_token_returns_value():
    with patch.dict(os.environ, {"WHATSAPP_ACCESS_TOKEN": "tok-xyz"}):
        assert _access_token() == "tok-xyz"


def test_access_token_raises_when_missing():
    with patch.dict(os.environ, {"WHATSAPP_ACCESS_TOKEN": ""}, clear=False):
        with pytest.raises(ValueError, match="WHATSAPP_ACCESS_TOKEN not configured"):
            _access_token()


def test_api_url_default():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("WHATSAPP_API_URL", None)
        assert "graph.facebook.com" in _api_url()


def test_api_url_custom():
    with patch.dict(os.environ, {"WHATSAPP_API_URL": "https://custom.api/"}):
        assert _api_url() == "https://custom.api"


def test_phone_number_id():
    with patch.dict(os.environ, {"WHATSAPP_PHONE_NUMBER_ID": "55199"}):
        assert _phone_number_id() == "55199"


# ── send_text_message (Meta provider) ────────────────────────────────────


@patch("app.services.whatsapp_providers.httpx.post")
def test_send_text_success(mock_post):
    mock_post.return_value = _success_response("wamid.text1")

    with patch.dict(os.environ, _ENV_META):
        result = WhatsAppService.send_text_message("+5511999990001", "Hello!")

    assert result.success is True
    assert result.provider_message_id == "wamid.text1"
    assert result.error_code is None


@patch("app.services.whatsapp_providers.httpx.post")
def test_send_text_api_error(mock_post):
    mock_post.return_value = _error_response(400, 131030, "Rate limit hit")

    with patch.dict(os.environ, _ENV_META):
        result = WhatsAppService.send_text_message("+5511999990001", "Hello!")

    assert result.success is False
    assert result.error_code == "131030"
    assert "Rate limit" in result.error_message


@patch("app.services.whatsapp_providers.httpx.post")
def test_send_text_timeout(mock_post):
    mock_post.side_effect = httpx.TimeoutException("timed out")

    with patch.dict(os.environ, _ENV_META):
        result = WhatsAppService.send_text_message("+5511999990001", "Hello!")

    assert result.success is False
    assert result.error_code == "TIMEOUT"


@patch("app.services.whatsapp_providers.httpx.post")
def test_send_text_unexpected_exception(mock_post):
    mock_post.side_effect = RuntimeError("connection reset")

    with patch.dict(os.environ, _ENV_META):
        result = WhatsAppService.send_text_message("+5511999990001", "Hello!")

    assert result.success is False
    assert result.error_code == "INTERNAL"
    assert "connection reset" in result.error_message


# ── send_template_message (Meta provider) ────────────────────────────────


@patch("app.services.whatsapp_providers.httpx.post")
def test_send_template_success(mock_post):
    mock_post.return_value = _success_response("wamid.tpl1")

    with patch.dict(os.environ, _ENV_META):
        result = WhatsAppService.send_template_message(
            "+5511999990001", "rfq_invite", params=["ABC Corp", "Copper"]
        )

    assert result.success is True
    assert result.provider_message_id == "wamid.tpl1"

    # Verify payload contains template components
    call_kwargs = mock_post.call_args
    sent_payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert sent_payload["type"] == "template"
    assert sent_payload["template"]["name"] == "rfq_invite"
    assert sent_payload["template"]["language"]["code"] == "pt_BR"


@patch("app.services.whatsapp_providers.httpx.post")
def test_send_template_no_params(mock_post):
    mock_post.return_value = _success_response("wamid.tpl2")

    with patch.dict(os.environ, _ENV_META):
        result = WhatsAppService.send_template_message(
            "+5511999990001", "simple_greeting"
        )

    assert result.success is True
    call_kwargs = mock_post.call_args
    sent_payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert sent_payload["template"]["components"] == []


@patch("app.services.whatsapp_providers.httpx.post")
def test_send_template_custom_language(mock_post):
    mock_post.return_value = _success_response()

    with patch.dict(os.environ, _ENV_META):
        WhatsAppService.send_template_message(
            "+5511999990001", "greeting", language_code="en_US"
        )

    call_kwargs = mock_post.call_args
    sent_payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert sent_payload["template"]["language"]["code"] == "en_US"


@patch("app.services.whatsapp_providers.httpx.post")
def test_send_template_api_error(mock_post):
    mock_post.return_value = _error_response(403, 10, "Not authorized")

    with patch.dict(os.environ, _ENV_META):
        result = WhatsAppService.send_template_message(
            "+5511999990001", "blocked_template"
        )

    assert result.success is False
    assert result.error_code == "10"


# ── URL construction ─────────────────────────────────────────────────────


def test_build_url():
    with patch.dict(os.environ, _ENV_META):
        url = WhatsAppService._build_url()
    assert url == "https://api.example.com/123456/messages"


@patch("app.services.whatsapp_providers.httpx.post")
def test_send_uses_correct_url(mock_post):
    mock_post.return_value = _success_response()

    with patch.dict(os.environ, _ENV_META):
        WhatsAppService.send_text_message("+5511999990001", "test")

    call_args = mock_post.call_args
    url_used = call_args[0][0] if call_args[0] else call_args.kwargs.get("url", "")
    assert "123456/messages" in url_used


@patch("app.services.whatsapp_providers.httpx.post")
def test_send_uses_bearer_token(mock_post):
    mock_post.return_value = _success_response()

    with patch.dict(os.environ, _ENV_META):
        WhatsAppService.send_text_message("+5511999990001", "test")

    call_kwargs = mock_post.call_args
    headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
    assert headers["Authorization"] == "Bearer test-token"


@patch("app.services.whatsapp_providers.httpx.post")
def test_send_success_empty_messages_array(mock_post):
    """API returns success but no messages array — msg_id defaults empty."""
    resp = MagicMock(spec=httpx.Response)
    resp.is_success = True
    resp.status_code = 200
    resp.json.return_value = {}
    mock_post.return_value = resp

    with patch.dict(os.environ, _ENV_META):
        result = WhatsAppService.send_text_message("+5511999990001", "test")

    assert result.success is True
    assert result.provider_message_id == ""


# ── provider factory ─────────────────────────────────────────────────────


def test_get_provider_meta():
    with patch.dict(os.environ, {"WHATSAPP_PROVIDER": "meta"}):
        assert get_provider_name() == "meta"
        assert isinstance(get_provider(), MetaWhatsAppProvider)


def test_get_provider_twilio():
    with patch.dict(os.environ, {"WHATSAPP_PROVIDER": "twilio"}):
        assert get_provider_name() == "twilio"
        assert isinstance(get_provider(), TwilioWhatsAppProvider)


def test_get_provider_fake():
    for name in ("fake", "mock", "test"):
        with patch.dict(os.environ, {"WHATSAPP_PROVIDER": name}):
            assert isinstance(get_provider(), FakeWhatsAppProvider)


def test_get_provider_unknown_falls_back_to_meta():
    with patch.dict(os.environ, {"WHATSAPP_PROVIDER": "nonexistent"}):
        assert get_provider_name() == "meta"


def test_get_provider_default_is_meta():
    env = os.environ.copy()
    env.pop("WHATSAPP_PROVIDER", None)
    with patch.dict(os.environ, env, clear=True):
        assert get_provider_name() == "meta"


# ── Twilio provider — send_text_message ──────────────────────────────────


@patch("app.services.whatsapp_providers.httpx.post")
def test_twilio_send_text_success(mock_post):
    mock_post.return_value = _twilio_success_response("SM999")

    with patch.dict(os.environ, _ENV_TWILIO):
        result = WhatsAppService.send_text_message("+5511999990001", "Hello Twilio!")

    assert result.success is True
    assert result.provider_message_id == "SM999"

    # Verify request structure (form-encoded, basic auth)
    call_kwargs = mock_post.call_args
    sent_data = call_kwargs.kwargs.get("data")
    assert sent_data["Body"] == "Hello Twilio!"
    assert sent_data["To"] == "whatsapp:+5511999990001"
    assert sent_data["From"] == "whatsapp:+14155238886"

    # Basic auth with SID:token
    auth = call_kwargs.kwargs.get("auth")
    assert auth == ("ACtest123", "test-auth-token")


@patch("app.services.whatsapp_providers.httpx.post")
def test_twilio_send_text_api_error(mock_post):
    mock_post.return_value = _twilio_error_response(400, 21211, "Invalid phone")

    with patch.dict(os.environ, _ENV_TWILIO):
        result = WhatsAppService.send_text_message("+000", "Hello!")

    assert result.success is False
    assert result.error_code == "21211"
    assert "Invalid phone" in result.error_message


@patch("app.services.whatsapp_providers.httpx.post")
def test_twilio_send_text_timeout(mock_post):
    mock_post.side_effect = httpx.TimeoutException("timed out")

    with patch.dict(os.environ, _ENV_TWILIO):
        result = WhatsAppService.send_text_message("+5511999990001", "Hello!")

    assert result.success is False
    assert result.error_code == "TIMEOUT"


@patch("app.services.whatsapp_providers.httpx.post")
def test_twilio_send_text_unexpected_exception(mock_post):
    mock_post.side_effect = RuntimeError("boom")

    with patch.dict(os.environ, _ENV_TWILIO):
        result = WhatsAppService.send_text_message("+5511999990001", "Hello!")

    assert result.success is False
    assert result.error_code == "INTERNAL"
    assert "boom" in result.error_message


# ── Twilio provider — send_template_message ──────────────────────────────


@patch("app.services.whatsapp_providers.httpx.post")
def test_twilio_send_template_fallback_text(mock_post):
    """Without a Content SID, Twilio falls back to plain text."""
    mock_post.return_value = _twilio_success_response("SM_tpl_1")

    env = {**_ENV_TWILIO}
    # No TWILIO_CONTENT_SID_RFQ_INVITE set
    with patch.dict(os.environ, env):
        result = WhatsAppService.send_template_message(
            "+5511999990001", "rfq_invite", params=["ABC Corp", "Copper"]
        )

    assert result.success is True
    call_kwargs = mock_post.call_args
    sent_data = call_kwargs.kwargs.get("data")
    assert "Body" in sent_data
    assert "[rfq_invite]" in sent_data["Body"]
    assert "ABC Corp" in sent_data["Body"]


@patch("app.services.whatsapp_providers.httpx.post")
def test_twilio_send_template_with_content_sid(mock_post):
    """With a Content SID env var, Twilio sends ContentSid + variables."""
    mock_post.return_value = _twilio_success_response("SM_tpl_2")

    env = {**_ENV_TWILIO, "TWILIO_CONTENT_SID_RFQ_INVITE": "HX123abc"}
    with patch.dict(os.environ, env):
        result = WhatsAppService.send_template_message(
            "+5511999990001", "rfq_invite", params=["ABC Corp", "Copper"]
        )

    assert result.success is True
    call_kwargs = mock_post.call_args
    sent_data = call_kwargs.kwargs.get("data")
    assert sent_data["ContentSid"] == "HX123abc"
    assert "ContentVariables" in sent_data
    # Should not have a Body key when using ContentSid
    assert "Body" not in sent_data


# ── Twilio provider — configuration errors ───────────────────────────────


def test_twilio_missing_account_sid():
    env = {**_ENV_TWILIO}
    env.pop("TWILIO_ACCOUNT_SID")
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("TWILIO_ACCOUNT_SID", None)
        result = WhatsAppService.send_text_message("+5511999990001", "Hello!")
    # Should fail gracefully with INTERNAL error (ValueError)
    assert result.success is False


def test_twilio_missing_auth_token():
    env = {**_ENV_TWILIO}
    env.pop("TWILIO_AUTH_TOKEN")
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("TWILIO_AUTH_TOKEN", None)
        result = WhatsAppService.send_text_message("+5511999990001", "Hello!")
    assert result.success is False


def test_twilio_missing_from_number():
    env = {**_ENV_TWILIO}
    env.pop("TWILIO_WHATSAPP_FROM")
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("TWILIO_WHATSAPP_FROM", None)
        result = WhatsAppService.send_text_message("+5511999990001", "Hello!")
    assert result.success is False


# ── Twilio provider — URL construction ───────────────────────────────────


def test_twilio_build_url():
    provider = TwilioWhatsAppProvider()
    with patch.dict(os.environ, {"TWILIO_ACCOUNT_SID": "AC123"}):
        url = provider._build_url()
    assert url == "https://api.twilio.com/2010-04-01/Accounts/AC123/Messages.json"


def test_twilio_normalize_phone():
    assert TwilioWhatsAppProvider._normalize_phone("+5511999990001") == "whatsapp:+5511999990001"
    assert TwilioWhatsAppProvider._normalize_phone("whatsapp:+5511999990001") == "whatsapp:+5511999990001"
    assert TwilioWhatsAppProvider._normalize_phone("  +5511999990001  ") == "whatsapp:+5511999990001"


def test_twilio_from_number_adds_prefix():
    provider = TwilioWhatsAppProvider()
    with patch.dict(os.environ, {"TWILIO_WHATSAPP_FROM": "+14155238886"}):
        assert provider._from_number() == "whatsapp:+14155238886"

    with patch.dict(os.environ, {"TWILIO_WHATSAPP_FROM": "whatsapp:+14155238886"}):
        assert provider._from_number() == "whatsapp:+14155238886"


# ── Fake provider ────────────────────────────────────────────────────────


def test_fake_provider_send_text():
    provider = FakeWhatsAppProvider()
    result = provider.send_text_message("+5511999990001", "test")
    assert result.success is True
    assert result.provider_message_id == "fake-+5511999990001"


def test_fake_provider_send_template():
    provider = FakeWhatsAppProvider()
    result = provider.send_template_message("+5511999990001", "rfq_invite", params=["A"])
    assert result.success is True
