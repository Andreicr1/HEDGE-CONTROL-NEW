"""Tests for the Westmetall background task and scheduler integration."""

from __future__ import annotations

import os
from datetime import date
from unittest.mock import MagicMock, patch

from app.services.westmetall_cash_settlement import (
    CircuitOpenError,
    WestmetallLayoutError,
    WestmetallFetchEvidence,
)
from app.tasks.westmetall_task import run_westmetall_ingestion
from app.tasks import scheduler as scheduler_mod


# ── Helpers ──────────────────────────────────────────────────────────


def _make_evidence() -> WestmetallFetchEvidence:
    return WestmetallFetchEvidence(
        source_url="https://example.com",
        html_sha256="abc123",
        fetched_at="2026-03-01T18:00:00Z",
    )


# ── run_westmetall_ingestion ─────────────────────────────────────────


class TestRunWestmetallIngestion:
    @patch("app.tasks.westmetall_task.SessionLocal")
    @patch("app.tasks.westmetall_task.ingest_westmetall_cash_settlement_daily_for_date")
    def test_success_logs_and_closes_session(self, mock_ingest, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_ingest.return_value = (3, 1, _make_evidence())

        run_westmetall_ingestion()

        mock_ingest.assert_called_once_with(mock_session, date.today())
        mock_session.close.assert_called_once()

    @patch("app.tasks.westmetall_task.SessionLocal")
    @patch("app.tasks.westmetall_task.ingest_westmetall_cash_settlement_daily_for_date")
    def test_layout_error_caught(self, mock_ingest, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_ingest.side_effect = WestmetallLayoutError("bad layout")

        # Should NOT raise
        run_westmetall_ingestion()

        mock_session.close.assert_called_once()

    @patch("app.tasks.westmetall_task.SessionLocal")
    @patch("app.tasks.westmetall_task.ingest_westmetall_cash_settlement_daily_for_date")
    def test_circuit_open_caught(self, mock_ingest, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_ingest.side_effect = CircuitOpenError("circuit open")

        run_westmetall_ingestion()

        mock_session.close.assert_called_once()


# ── Scheduler start/stop ─────────────────────────────────────────────


class TestScheduler:
    def test_scheduler_disabled_when_env_set(self):
        """When SCHEDULER_DISABLED=1, start_scheduler should be a no-op."""
        with patch.dict(os.environ, {"SCHEDULER_DISABLED": "1"}):
            scheduler_mod._scheduler = None
            scheduler_mod.start_scheduler()
            assert scheduler_mod._scheduler is None

    def test_scheduler_starts_and_stops(self):
        """Scheduler starts, registers a job, then shuts down cleanly."""
        with patch.dict(os.environ, {"SCHEDULER_DISABLED": ""}):
            scheduler_mod._scheduler = None
            scheduler_mod.start_scheduler()
            assert scheduler_mod._scheduler is not None
            jobs = scheduler_mod._scheduler.get_jobs()
            assert any(j.id == "westmetall_daily_ingestion" for j in jobs)

            scheduler_mod.stop_scheduler()
            assert scheduler_mod._scheduler is None
