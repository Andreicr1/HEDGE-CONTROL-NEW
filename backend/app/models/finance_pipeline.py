"""Finance Pipeline Run / Step models."""

from __future__ import annotations

import enum
import hashlib
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class PipelineRunStatus(enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"
    partial = "partial"


class PipelineStepStatus(enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


PIPELINE_STEPS = [
    "market_snapshot",
    "mtm_computation",
    "pl_snapshot",
    "cashflow_baseline",
    "risk_flags",
    "summary",
]


class FinancePipelineRun(Base):
    __tablename__ = "finance_pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PipelineRunStatus] = mapped_column(
        Enum(PipelineRunStatus, name="pipeline_run_status"),
        nullable=False,
        default=PipelineRunStatus.running,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    steps_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    steps_total: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    inputs_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    steps: Mapped[list["FinancePipelineStep"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="FinancePipelineStep.step_number",
    )

    @staticmethod
    def compute_hash(run_date: date) -> str:
        return hashlib.sha256(str(run_date).encode()).hexdigest()


class FinancePipelineStep(Base):
    __tablename__ = "finance_pipeline_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("finance_pipeline_runs.id"), nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[PipelineStepStatus] = mapped_column(
        Enum(PipelineStepStatus, name="pipeline_step_status"),
        nullable=False,
        default=PipelineStepStatus.pending,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped["FinancePipelineRun"] = relationship(back_populates="steps")
