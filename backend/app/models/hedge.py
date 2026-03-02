"""Hedge model — represents a hedge position against commodity exposure."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class HedgeDirection(enum.Enum):
    buy = "buy"
    sell = "sell"


class HedgeStatus(enum.Enum):
    active = "active"
    partially_settled = "partially_settled"
    settled = "settled"
    cancelled = "cancelled"


class HedgeSourceType(enum.Enum):
    rfq_award = "rfq_award"
    manual = "manual"
    auto = "auto"


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class Hedge(Base):
    __tablename__ = "hedges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reference: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    counterparty_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=False
    )

    commodity: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[HedgeDirection] = mapped_column(
        Enum(HedgeDirection, name="hedge_direction"), nullable=False
    )
    tons: Mapped[float] = mapped_column(Numeric(15, 3), nullable=False)
    price_per_ton: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    premium_discount: Mapped[float] = mapped_column(
        Numeric(15, 2), default=0, nullable=False
    )

    settlement_date: Mapped[date] = mapped_column(Date, nullable=False)
    prompt_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[HedgeStatus] = mapped_column(
        Enum(HedgeStatus, name="hedge_status"),
        default=HedgeStatus.active,
        nullable=False,
    )

    source_type: Mapped[HedgeSourceType] = mapped_column(
        Enum(HedgeSourceType, name="hedge_source_type"), nullable=False
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hedge_contracts.id"), nullable=True
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
