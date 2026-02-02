from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class MTMObjectType(str, Enum):
    hedge_contract = "hedge_contract"
    order = "order"


class MTMResultResponse(BaseModel):
    object_type: MTMObjectType
    object_id: str
    as_of_date: date
    mtm_value: Decimal
    price_d1: Decimal
    entry_price: Decimal
    quantity_mt: Decimal


class MTMSnapshotCreate(BaseModel):
    object_type: MTMObjectType
    object_id: str
    as_of_date: date
    correlation_id: str = Field(..., description="Caller-provided correlation id for evidence")


class MTMSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    object_type: MTMObjectType
    object_id: str
    as_of_date: date
    mtm_value: Decimal
    price_d1: Decimal
    entry_price: Decimal
    quantity_mt: Decimal
    correlation_id: str
    created_at: datetime

