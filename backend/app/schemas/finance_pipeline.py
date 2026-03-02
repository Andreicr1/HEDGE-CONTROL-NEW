"""Schemas for Finance Pipeline."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PipelineStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    step_number: int
    step_name: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    records_processed: int = 0
    error_message: Optional[str] = None


class PipelineRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_date: date
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    steps_completed: int
    steps_total: int
    error_message: Optional[str] = None
    inputs_hash: str
    created_at: datetime


class PipelineRunDetailRead(PipelineRunRead):
    steps: list[PipelineStepRead] = []


class PipelineRunListResponse(BaseModel):
    items: list[PipelineRunRead]


class TriggerPipelineRequest(BaseModel):
    run_date: date
