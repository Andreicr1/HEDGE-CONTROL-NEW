from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

class PLResultResponse(BaseModel):
    realized_pl: Decimal
    unrealized_mtm: Decimal

class PLSnapshotCreate(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    period_start: date
    period_end: date

class PLSnapshotResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    period_start: date
    period_end: date
    realized_pl: Decimal
    unrealized_mtm: Decimal
    created_at: datetime
    correlation_id: Optional[uuid.UUID]

    class Config:
        orm_mode = True