import enum
import uuid

from sqlalchemy import DateTime, Enum, Float, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OrderType(enum.Enum):
    sales = "SO"
    purchase = "PO"


class PriceType(enum.Enum):
    fixed = "fixed"
    variable = "variable"


class OrderPricingConvention(enum.Enum):
    avg = "AVG"
    avginter = "AVGInter"
    c2r = "C2R"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_type: Mapped[OrderType] = mapped_column(Enum(OrderType, name="order_type"), nullable=False)
    price_type: Mapped[PriceType] = mapped_column(Enum(PriceType, name="price_type"), nullable=False)
    quantity_mt: Mapped[float] = mapped_column(Float, nullable=False)
    pricing_convention: Mapped[OrderPricingConvention | None] = mapped_column(
        Enum(OrderPricingConvention, name="order_pricing_convention"),
        nullable=True,
    )
    avg_entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
