import enum
import uuid

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class HedgeLegSide(enum.Enum):
    buy = "buy"
    sell = "sell"


class HedgeClassification(enum.Enum):
    long = "long"
    short = "short"


class HedgeContractStatus(enum.Enum):
    active = "active"
    cancelled = "cancelled"
    settled = "settled"


class HedgeContract(Base):
    __tablename__ = "hedge_contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    commodity: Mapped[str] = mapped_column(String(length=64), nullable=False)
    quantity_mt: Mapped[float] = mapped_column(Float, nullable=False)
    rfq_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfqs.id", ondelete="RESTRICT"), nullable=True
    )
    rfq_quote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfq_quotes.id", ondelete="RESTRICT"), nullable=True
    )
    counterparty_id: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
    fixed_price_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    fixed_price_unit: Mapped[str | None] = mapped_column(String(length=32), nullable=True)
    float_pricing_convention: Mapped[str | None] = mapped_column(String(length=64), nullable=True)
    status: Mapped[HedgeContractStatus] = mapped_column(
        Enum(HedgeContractStatus, name="hedge_contract_status"),
        nullable=False,
        default=HedgeContractStatus.active,
    )
    fixed_leg_side: Mapped[HedgeLegSide] = mapped_column(
        Enum(HedgeLegSide, name="hedge_leg_side"),
        nullable=False,
    )
    variable_leg_side: Mapped[HedgeLegSide] = mapped_column(
        Enum(HedgeLegSide, name="hedge_leg_side"),
        nullable=False,
    )
    classification: Mapped[HedgeClassification] = mapped_column(
        Enum(HedgeClassification, name="hedge_classification"),
        nullable=False,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
