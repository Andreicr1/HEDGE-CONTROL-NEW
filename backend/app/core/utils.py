"""Shared utility helpers used across the application."""

from __future__ import annotations

from datetime import datetime, timezone


def now_utc() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)
