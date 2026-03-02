"""WhatsApp webhook endpoints.

- ``GET /webhooks/whatsapp`` — Meta challenge verification
- ``POST /webhooks/whatsapp`` — receive inbound messages
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.logging import get_logger
from app.services.webhook_processor import (
    enqueue_message,
    extract_messages,
    verify_signature,
)

logger = get_logger()
router = APIRouter()


@router.get("/whatsapp")
def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
) -> int:
    """Meta webhook verification — echo the challenge if token matches.

    Meta sends a GET with ``hub.mode=subscribe``, ``hub.verify_token`` and
    ``hub.challenge``.  We must respond with the challenge value as an
    integer.
    """
    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    if hub_mode != "subscribe" or hub_verify_token != expected_token:
        logger.warning(
            "webhook_verify_failed",
            hub_mode=hub_mode,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verification failed",
        )
    logger.info("webhook_verified")
    return int(hub_challenge)


@router.post("/whatsapp", status_code=200)
async def receive_webhook(request: Request) -> dict[str, str]:
    """Receive inbound WhatsApp messages from Meta.

    1. Validate HMAC signature (``X-Hub-Signature-256``).
    2. Extract text messages from the nested payload.
    3. Enqueue each message for async processing.
    4. Return 200 immediately (Meta requires < 5 s response).
    """
    body = await request.body()

    # Signature validation
    signature = request.headers.get("X-Hub-Signature-256", "")
    if signature and not verify_signature(body, signature):
        logger.warning("webhook_invalid_signature")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signature",
        )

    import json

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

    logger.info(
        "webhook_processed",
        messages_received=len(messages),
    )
    return {"status": "ok"}
