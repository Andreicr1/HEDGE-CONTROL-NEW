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

    1. Send reminders for RFQs below the response threshold.
    2. Close or promote RFQs that exceeded the timeout window.
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
        reminded = RFQOrchestrator.send_reminders(
            session, min_response_rate=reminder_threshold
        )
        timed_out = RFQOrchestrator.check_rfq_timeouts(
            session, timeout_hours=timeout_hours
        )
        session.commit()

        logger.info(
            "rfq_timeout_task_done",
            reminded_count=len(reminded),
            timed_out_count=len(timed_out),
        )
    except Exception:
        session.rollback()
        logger.exception("rfq_timeout_task_error")
    finally:
        session.close()
