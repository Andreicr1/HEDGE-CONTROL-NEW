import uuid

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RFQQuote(Base):
    __tablename__ = "rfq_quotes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rfqs.id", ondelete="RESTRICT"), nullable=False
    )
    counterparty_id: Mapped[str] = mapped_column(String(length=64), nullable=False)
    fixed_price_value: Mapped[float] = mapped_column("price_value", Float, nullable=False)
    fixed_price_unit: Mapped[str] = mapped_column("price_unit", String(length=32), nullable=False)
    float_pricing_convention: Mapped[str] = mapped_column("pricing_convention", String(length=64), nullable=False)
    received_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
