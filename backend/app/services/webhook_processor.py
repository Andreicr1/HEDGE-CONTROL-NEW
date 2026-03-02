"""Webhook processor — parses and enqueues inbound WhatsApp messages.

The processor:
1. Validates the HMAC-SHA256 signature from Meta.
2. Extracts individual messages from the webhook payload.
3. Enqueues them as ``WhatsAppInboundMessage`` objects for downstream
   consumers (LLM Agent, RFQ Orchestrator).

The queue is an in-process :class:`asyncio.Queue` for now; it can be swapped
for a durable message broker (Service Bus, Redis Streams) when needed.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from collections import deque
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.schemas.whatsapp import WhatsAppInboundMessage

logger = get_logger()

# ---------------------------------------------------------------------------
# In-process message queue (replaced by broker in production)
# ---------------------------------------------------------------------------

_message_queue: deque[WhatsAppInboundMessage] = deque(maxlen=10_000)

_SEEN_IDS_MAX = 5_000
_seen_message_ids: deque[str] = deque(maxlen=_SEEN_IDS_MAX)
_seen_set: set[str] = set()


def enqueue_message(msg: WhatsAppInboundMessage) -> None:
    """Add a parsed inbound message to the processing queue.

    Silently drops duplicates (WhatsApp may redeliver webhooks).
    """
    if msg.message_id in _seen_set:
        logger.debug("webhook_duplicate_skipped", message_id=msg.message_id)
        return

    if len(_seen_message_ids) >= _SEEN_IDS_MAX:
        evicted = _seen_message_ids[0]
        _seen_set.discard(evicted)
    _seen_message_ids.append(msg.message_id)
    _seen_set.add(msg.message_id)

    _message_queue.append(msg)
    logger.info(
        "webhook_message_enqueued",
        message_id=msg.message_id,
        from_phone=msg.from_phone,
        queue_depth=len(_message_queue),
    )


def dequeue_message() -> WhatsAppInboundMessage | None:
    """Pop the oldest message from the queue, or ``None`` if empty."""
    try:
        return _message_queue.popleft()
    except IndexError:
        return None


def queue_depth() -> int:
    """Return the current number of messages waiting."""
    return len(_message_queue)


def drain_queue() -> list[WhatsAppInboundMessage]:
    """Remove and return all messages from the queue (useful in tests)."""
    msgs = list(_message_queue)
    _message_queue.clear()
    return msgs


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def verify_signature(payload_body: bytes, signature_header: str) -> bool:
    """Validate the ``X-Hub-Signature-256`` from Meta.

    Parameters
    ----------
    payload_body:
        Raw request body bytes.
    signature_header:
        Value of the ``X-Hub-Signature-256`` header (``sha256=<hex>``).

    Returns
    -------
    bool
        ``True`` if the HMAC matches.
    """
    app_secret = os.getenv("WHATSAPP_APP_SECRET", "")
    if not app_secret:
        logger.warning("whatsapp_app_secret_missing")
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected = signature_header[7:]  # strip 'sha256='
    computed = hmac.new(
        app_secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, expected)


# ---------------------------------------------------------------------------
# Payload extraction
# ---------------------------------------------------------------------------


def extract_messages(payload: dict[str, Any]) -> list[WhatsAppInboundMessage]:
    """Extract individual text messages from a Meta webhook payload.

    Meta sends a nested structure::

        {
          "object": "whatsapp_business_account",
          "entry": [{
            "changes": [{
              "value": {
                "contacts": [{"wa_id": "...", "profile": {"name": "..."}}],
                "messages": [{"id": "...", "from": "...", "timestamp": "...",
                              "type": "text", "text": {"body": "..."}}]
              }
            }]
          }]
        }

    We only process ``type == "text"`` messages.
    """
    messages: list[WhatsAppInboundMessage] = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contacts = {
                c.get("wa_id", ""): c.get("profile", {}).get("name")
                for c in value.get("contacts", [])
            }
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue
                from_phone = msg.get("from", "")
                ts_str = msg.get("timestamp", "0")
                try:
                    ts = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
                except (ValueError, OSError):
                    ts = datetime.now(timezone.utc)

                text_body = msg.get("text", {}).get("body", "")
                messages.append(
                    WhatsAppInboundMessage(
                        message_id=msg.get("id", ""),
                        from_phone=from_phone,
                        timestamp=ts,
                        text=text_body,
                        sender_name=contacts.get(from_phone),
                    )
                )

    return messages
