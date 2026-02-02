from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderType(str, Enum):
    sales = "SO"
    purchase = "PO"


class PriceType(str, Enum):
    fixed = "fixed"
    variable = "variable"


class OrderPricingConvention(str, Enum):
    avg = "AVG"
    avginter = "AVGInter"
    c2r = "C2R"


class OrderBase(BaseModel):
    price_type: PriceType = Field(..., description="Fixed or variable pricing")
    quantity_mt: float = Field(..., description="Quantity in metric tons (MT)")
    pricing_convention: OrderPricingConvention | None = Field(
        None, description="Required only for variable orders (AVG, AVGInter, C2R)"
    )
    avg_entry_price: float | None = Field(None, description="Required only for variable orders (USD/MT)")


class SalesOrderCreate(OrderBase):
    pass


class PurchaseOrderCreate(OrderBase):
    pass


class OrderRead(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_type: OrderType
    created_at: datetime
