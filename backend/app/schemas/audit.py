from __future__ import annotations

import base64
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    timestamp_utc: datetime
    entity_type: str = Field(..., max_length=64)
    entity_id: uuid.UUID
    event_type: str = Field(..., max_length=64)
    payload: object
    checksum: str = Field(..., max_length=128)
    signature: str | None = Field(None, max_length=256)

    @field_validator("signature", mode="before")
    @classmethod
    def _bytes_to_b64(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, bytes):
            return base64.b64encode(v).decode("ascii")
        return v


class AuditEventListResponse(BaseModel):
    events: list[AuditEventRead] = Field(default_factory=list)
    next_cursor: str | None = Field(None, max_length=256)
