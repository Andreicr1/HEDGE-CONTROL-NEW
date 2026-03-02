"""Schemas for Hedge (1.4)."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class HedgeDirection(str, Enum):
    buy = "buy"
    sell = "sell"


class HedgeStatus(str, Enum):
    active = "active"
    partially_settled = "partially_settled"
    settled = "settled"
    cancelled = "cancelled"


class HedgeSourceType(str, Enum):
    rfq_award = "rfq_award"
    manual = "manual"
    auto = "auto"


# ---------------------------------------------------------------------------
# Create / Update / Read
# ---------------------------------------------------------------------------


class HedgeCreate(BaseModel):
    counterparty_id: UUID
    commodity: str
    direction: HedgeDirection
    tons: float
    price_per_ton: float
    premium_discount: float = 0
    settlement_date: date
    prompt_date: Optional[date] = None
    trade_date: Optional[date] = None  # defaults to today in service
    source_type: HedgeSourceType = HedgeSourceType.manual
    source_id: Optional[UUID] = None
    contract_id: Optional[UUID] = None
    notes: Optional[str] = None
    exposure_id: Optional[UUID] = None  # if provided, will link to exposure


class HedgeUpdate(BaseModel):
    commodity: Optional[str] = None
    direction: Optional[HedgeDirection] = None
    tons: Optional[float] = None
    price_per_ton: Optional[float] = None
    premium_discount: Optional[float] = None
    settlement_date: Optional[date] = None
    prompt_date: Optional[date] = None
    notes: Optional[str] = None


class HedgeStatusUpdate(BaseModel):
    status: HedgeStatus


class HedgeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference: str
    counterparty_id: UUID
    commodity: str
    direction: HedgeDirection
    tons: float
    price_per_ton: float
    premium_discount: float
    settlement_date: date
    prompt_date: Optional[date] = None
    trade_date: date
    status: HedgeStatus
    source_type: HedgeSourceType
    source_id: Optional[UUID] = None
    contract_id: Optional[UUID] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class HedgeListResponse(BaseModel):
    items: list[HedgeRead]
    next_cursor: Optional[str] = None
