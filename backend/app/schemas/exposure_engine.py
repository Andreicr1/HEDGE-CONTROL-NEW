"""Schemas for the Exposure Engine (1.3)."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums (mirror model enums)
# ---------------------------------------------------------------------------


class ExposureDirection(str, Enum):
    long = "long"
    short = "short"


class ExposureSourceType(str, Enum):
    sales_order = "sales_order"
    purchase_order = "purchase_order"


class ExposureStatus(str, Enum):
    open = "open"
    partially_hedged = "partially_hedged"
    fully_hedged = "fully_hedged"
    cancelled = "cancelled"


class HedgeTaskAction(str, Enum):
    hedge_new = "hedge_new"
    increase = "increase"
    decrease = "decrease"
    cancel = "cancel"


class HedgeTaskStatus(str, Enum):
    pending = "pending"
    executed = "executed"
    cancelled = "cancelled"


# ---------------------------------------------------------------------------
# Exposure read / list
# ---------------------------------------------------------------------------


class ExposureDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    commodity: str
    direction: ExposureDirection
    source_type: ExposureSourceType
    source_id: UUID
    original_tons: float
    open_tons: float
    hedged_tons: float = 0.0
    price_per_ton: Optional[float] = None
    settlement_month: Optional[str] = None
    status: ExposureStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Enriched from related order (populated by list endpoint)
    price_type: Optional[str] = None
    order_type: Optional[str] = None
    counterparty_name: Optional[str] = None
    pricing_convention: Optional[str] = None
    reference_month: Optional[str] = None
    observation_date_start: Optional[date] = None
    observation_date_end: Optional[date] = None
    fixing_date: Optional[date] = None
    avg_entry_price: Optional[float] = None
    order_notes: Optional[str] = None
    delivery_date_start: Optional[date] = None
    delivery_date_end: Optional[date] = None


class ExposureListResponse(BaseModel):
    items: list[ExposureDetailRead]
    next_cursor: Optional[str] = None


# ---------------------------------------------------------------------------
# Net exposure
# ---------------------------------------------------------------------------


class NetExposureItem(BaseModel):
    commodity: str
    long_tons: float
    short_tons: float
    net_tons: float
    long_original: float = 0.0
    short_original: float = 0.0
    long_hedged: float = 0.0
    short_hedged: float = 0.0


class NetExposureResponse(BaseModel):
    items: list[NetExposureItem]


# ---------------------------------------------------------------------------
# Hedge Tasks
# ---------------------------------------------------------------------------


class HedgeTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    exposure_id: UUID
    recommended_tons: float
    recommended_action: HedgeTaskAction
    status: HedgeTaskStatus
    created_at: datetime
    executed_at: Optional[datetime] = None


class HedgeTaskListResponse(BaseModel):
    items: list[HedgeTaskRead]
    next_cursor: Optional[str] = None


# ---------------------------------------------------------------------------
# Reconcile response
# ---------------------------------------------------------------------------


class ReconcileResponse(BaseModel):
    created: int = 0
    updated: int = 0
    message: str = "Reconciliation completed"
