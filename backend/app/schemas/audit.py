from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    timestamp_utc: datetime
    entity_type: str
    entity_id: uuid.UUID
    event_type: str
    payload: object
    checksum: str
    signature: bytes | None = None


class AuditEventListResponse(BaseModel):
    events: list[AuditEventRead] = Field(default_factory=list)
    next_cursor: str | None = None