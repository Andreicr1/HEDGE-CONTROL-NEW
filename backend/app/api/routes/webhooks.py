"""WhatsApp webhook endpoints.

- ``GET /webhooks/whatsapp`` — Meta challenge verification
- ``POST /webhooks/whatsapp`` — receive inbound messages and trigger processing
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.logging import get_logger
from app.services.webhook_processor import (
    enqueue_message,
    extract_messages,
    verify_signature,
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
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
) -> int:
    """Meta webhook verification — echo the challenge if token matches."""
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    if hub_mode != "subscribe" or hub_verify_token != expected_token:
        logger.warning("webhook_verify_failed", hub_mode=hub_mode)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verification failed",
        )
    logger.info("webhook_verified")
    return int(hub_challenge)


@router.post("/whatsapp", status_code=200)
async def receive_webhook(request: Request) -> dict[str, str]:
    """Receive inbound WhatsApp messages from Meta.

    1. Validate HMAC signature.
    2. Extract text messages from the nested payload.
    3. Enqueue each message.
    4. Submit background task to drain the queue (LLM → auto-quote).
    5. Return 200 immediately (Meta requires < 5 s response).
    """
    body = await request.body()

    signature = request.headers.get("X-Hub-Signature-256", "")
    if signature and not verify_signature(body, signature):
        logger.warning("webhook_invalid_signature")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signature",
        )

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

    logger.info("webhook_processed", messages_received=len(messages))
    return {"status": "ok"}
