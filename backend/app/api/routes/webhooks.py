"""WhatsApp webhook endpoints.

Supports two inbound providers based on ``WHATSAPP_PROVIDER``:

**Meta Cloud API** (default):
- ``GET  /webhooks/whatsapp`` — Meta challenge verification
- ``POST /webhooks/whatsapp`` — receive inbound messages (JSON + HMAC)

**Twilio**:
- ``GET  /webhooks/whatsapp`` — returns 200 (Twilio doesn't verify)
- ``POST /webhooks/whatsapp`` — receive inbound messages (form-encoded + X-Twilio-Signature)
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.logging import get_logger
from app.services.whatsapp_providers import get_provider_name
from app.services.webhook_processor import (
    enqueue_message,
    extract_messages,
    extract_messages_twilio,
    verify_signature,
    verify_twilio_signature,
)

logger = get_logger()
router = APIRouter()

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rfq-inbound")


def _process_queue_in_background() -> None:
    """Drain the inbound queue in a background thread so the webhook
    returns 200 within Meta's 5-second window."""
    from app.core.database import SessionLocal
    from app.services.rfq_orchestrator import RFQOrchestrator

    session = SessionLocal()
    try:
        results = RFQOrchestrator.process_inbound_queue(session)
        if results:
            logger.info(
                "webhook_background_processed",
                processed_count=len(results),
                statuses=[r.get("status") for r in results],
            )
    except Exception:
        session.rollback()
        logger.exception("webhook_background_processing_error")
    finally:
        session.close()


@router.get("/whatsapp")
def verify_webhook(
    request: Request,
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
) -> int | dict[str, str]:
    """Webhook verification.

    - **Meta**: echoes ``hub.challenge`` if verify token matches.
    - **Twilio**: no verification needed — returns 200.
    """
    provider = get_provider_name()

    if provider == "twilio":
        logger.info("webhook_twilio_get_ok")
        return {"status": "ok"}

    # Meta verification
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    if hub_mode != "subscribe" or hub_verify_token != expected_token:
        logger.warning("webhook_verify_failed", hub_mode=hub_mode)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verification failed",
        )
    logger.info("webhook_verified")
    return int(hub_challenge or "0")


@router.post("/whatsapp", status_code=200)
async def receive_webhook(request: Request) -> dict[str, str]:
    """Receive inbound WhatsApp messages.

    Provider-aware:

    - **Meta** (JSON body + HMAC-SHA256 via ``X-Hub-Signature-256``)
    - **Twilio** (form-encoded body + ``X-Twilio-Signature``)

    In both cases, messages are enqueued and a background task drains
    the queue via ``RFQOrchestrator``.  Returns 200 immediately to
    meet provider timeout requirements.
    """
    provider = get_provider_name()

    if provider == "twilio":
        return await _receive_twilio(request)
    return await _receive_meta(request)


async def _receive_meta(request: Request) -> dict[str, str]:
    """Handle Meta Cloud API inbound webhook."""
    body = await request.body()

    signature = request.headers.get("X-Hub-Signature-256", "")
    app_secret_configured = bool(os.getenv("WHATSAPP_APP_SECRET", ""))

    if app_secret_configured:
        if not signature:
            logger.warning("webhook_missing_signature")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing signature",
            )
        if not verify_signature(body, signature):
            logger.warning("webhook_invalid_signature")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid signature",
            )
    elif signature:
        logger.warning("webhook_signature_present_but_secret_not_configured")
    else:
        logger.warning("webhook_no_hmac_verification")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        )

    messages = extract_messages(payload)
    for msg in messages:
        enqueue_message(msg)

    if messages:
        _executor.submit(_process_queue_in_background)

    logger.info("webhook_processed", provider="meta", messages_received=len(messages))
    return {"status": "ok"}


async def _receive_twilio(request: Request) -> dict[str, str]:
    """Handle Twilio inbound webhook (form-encoded)."""
    form_data = await request.form()
    form_params: dict[str, str] = {k: str(v) for k, v in form_data.items()}

    # Signature verification
    twilio_signature = request.headers.get("X-Twilio-Signature", "")
    auth_token_configured = bool(os.getenv("TWILIO_AUTH_TOKEN", ""))

    if auth_token_configured:
        # Reconstruct the full URL as Twilio sees it
        webhook_url = os.getenv("TWILIO_WEBHOOK_URL", str(request.url))
        if not twilio_signature:
            logger.warning("webhook_twilio_missing_signature")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing Twilio signature",
            )
        if not verify_twilio_signature(webhook_url, form_params, twilio_signature):
            logger.warning("webhook_twilio_invalid_signature")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature",
            )
    else:
        logger.warning("webhook_twilio_no_signature_verification")

    messages = extract_messages_twilio(form_params)
    for msg in messages:
        enqueue_message(msg)

    if messages:
        _executor.submit(_process_queue_in_background)

    logger.info(
        "webhook_processed", provider="twilio", messages_received=len(messages)
    )
    return {"status": "ok"}
