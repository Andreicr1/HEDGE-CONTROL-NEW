"""Reusable cursor-based pagination helper.

Encodes / decodes cursors as ``base64(created_at_iso|uuid)`` and provides
a generic ``paginate()`` function that works with any SQLAlchemy model that
has ``created_at`` and ``id`` columns.
"""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.orm import Query


def encode_cursor(created_at: datetime, entity_id: UUID) -> str:
    """Encode a (timestamp, uuid) pair into a URL-safe cursor string."""
    raw = f"{created_at.isoformat()}|{entity_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Decode a cursor string back into (timestamp, uuid)."""
    decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
    ts_str, id_str = decoded.split("|", maxsplit=1)
    return datetime.fromisoformat(ts_str), UUID(id_str)


def paginate(
    query: Query,
    *,
    created_at_col: Column,
    id_col: Column,
    cursor: str | None = None,
    limit: int = 50,
    ts_attr: str = "created_at",
    id_attr: str = "id",
) -> tuple[Sequence[Any], str | None]:
    """Apply cursor-based pagination to *query*.

    Returns ``(items, next_cursor)``.  ``next_cursor`` is ``None`` when
    there are no more pages.

    *ts_attr* / *id_attr* control which model attributes are read when
    building the next-page cursor (default: ``created_at`` / ``id``).
    """
    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)
        query = query.filter(
            (created_at_col > cursor_ts)
            | ((created_at_col == cursor_ts) & (id_col > cursor_id))
        )

    rows = query.order_by(created_at_col.asc(), id_col.asc()).limit(limit + 1).all()

    next_cursor: str | None = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = encode_cursor(
            getattr(last, ts_attr),
            getattr(last, id_attr),
        )
        rows = rows[:limit]

    return rows, next_cursor
