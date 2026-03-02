"""Scheduled task — checks RFQ response timeouts and sends reminders.

Configurable via env vars:
    RFQ_TIMEOUT_HOURS         Default 24  — hours before a SENT RFQ times out.
    RFQ_REMINDER_THRESHOLD    Default 0.5 — response rate below which reminders fire.
    RFQ_TIMEOUT_CRON_MINUTE   Default 0   — cron minute for the task (every hour by default).
"""

from __future__ import annotations

import os

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.services.rfq_orchestrator import RFQOrchestrator

logger = get_logger()


def run_rfq_timeout_check() -> None:
    """Entry-point called by APScheduler every hour (default).

    Flags (but does NOT auto-transition) RFQs that:
    1. Have low counterparty response rates.
    2. Have exceeded the response timeout window.

    The trader reviews flagged RFQs in the UI and decides to
    refresh, award, or reject.
    """
    timeout_hours = int(os.getenv("RFQ_TIMEOUT_HOURS", "24"))
    reminder_threshold = float(os.getenv("RFQ_REMINDER_THRESHOLD", "0.5"))

    logger.info(
        "rfq_timeout_task_start",
        timeout_hours=timeout_hours,
        reminder_threshold=reminder_threshold,
    )

    session = SessionLocal()
    try:
        low_response = RFQOrchestrator.check_low_response_rfqs(
            session, min_response_rate=reminder_threshold
        )
        timed_out = RFQOrchestrator.check_rfq_timeouts(
            session, timeout_hours=timeout_hours
        )

        logger.info(
            "rfq_timeout_task_done",
            low_response_count=len(low_response),
            timed_out_count=len(timed_out),
        )
    except Exception:
        logger.exception("rfq_timeout_task_error")
    finally:
        session.close()
