"""Schemas for the Exposure Engine (1.3)."""

from datetime import datetime
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
    price_per_ton: Optional[float] = None
    settlement_month: Optional[str] = None
    status: ExposureStatus
    created_at: datetime
    updated_at: Optional[datetime] = None


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
