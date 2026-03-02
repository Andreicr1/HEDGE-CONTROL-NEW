"""Scheduled background task for daily Westmetall cash-settlement scraping.

Runs every day at 18:00 UTC (after LME close).  The task uses the same
``ingest_westmetall_cash_settlement_daily_for_date`` service that the manual
endpoint exposes, so results are persisted identically.

The scheduler is isolated: a failure inside the task never propagates to the
FastAPI request/response cycle.
"""

from __future__ import annotations

from datetime import date

from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.services.cash_settlement_prices import (
    ingest_westmetall_cash_settlement_daily_for_date,
)
from app.services.westmetall_cash_settlement import (
    CircuitOpenError,
    WestmetallLayoutError,
)

logger = get_logger()


def run_westmetall_ingestion() -> None:
    """Execute one Westmetall ingestion cycle for today's date.

    Creates its own DB session so it is fully independent of the request cycle.
    All exceptions are caught and logged — the scheduler must never crash.
    """
    settlement_date = date.today()
    logger.info(
        "westmetall_task_start",
        settlement_date=settlement_date.isoformat(),
    )
    session = SessionLocal()
    try:
        ingested, skipped, evidence = ingest_westmetall_cash_settlement_daily_for_date(
            session, settlement_date
        )
        logger.info(
            "westmetall_task_success",
            settlement_date=settlement_date.isoformat(),
            ingested_count=ingested,
            skipped_count=skipped,
            source_url=evidence.source_url,
        )
    except WestmetallLayoutError as exc:
        logger.error(
            "westmetall_task_layout_error",
            settlement_date=settlement_date.isoformat(),
            error=str(exc),
        )
    except CircuitOpenError as exc:
        logger.warning(
            "westmetall_task_circuit_open",
            settlement_date=settlement_date.isoformat(),
            error=str(exc),
        )
    except Exception as exc:  # pragma: no cover — safety net
        logger.error(
            "westmetall_task_unexpected_error",
            settlement_date=settlement_date.isoformat(),
            error=str(exc),
            exc_info=True,
        )
    finally:
        session.close()
