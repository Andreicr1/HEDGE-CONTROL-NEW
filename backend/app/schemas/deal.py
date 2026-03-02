"""Schemas for Deal Engine (component 1.5)."""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DealStatus(str, Enum):
    open = "open"
    partially_hedged = "partially_hedged"
    fully_hedged = "fully_hedged"
    settled = "settled"
    closed = "closed"


class DealLinkedType(str, Enum):
    sales_order = "sales_order"
    purchase_order = "purchase_order"
    hedge = "hedge"
    contract = "contract"


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------


class DealCreate(BaseModel):
    name: str
    commodity: str
    links: list["DealLinkCreate"] = []


class DealLinkCreate(BaseModel):
    linked_type: DealLinkedType
    linked_id: UUID


class DealLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deal_id: UUID
    linked_type: DealLinkedType
    linked_id: UUID
    created_at: datetime


class DealPNLSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deal_id: UUID
    snapshot_date: date
    physical_revenue: float
    physical_cost: float
    hedge_pnl_realized: float
    hedge_pnl_mtm: float
    total_pnl: float
    inputs_hash: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


class DealRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference: str
    name: str
    commodity: str
    status: DealStatus
    total_physical_tons: float
    total_hedge_tons: float
    hedge_ratio: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_deleted: bool


class DealDetailRead(DealRead):
    """Deal detail with links and latest P&L snapshot."""

    links: list[DealLinkRead] = []
    latest_pnl: Optional[DealPNLSnapshotRead] = None


class DealListResponse(BaseModel):
    items: list[DealRead]
    next_cursor: Optional[str] = None


class DealPNLHistoryResponse(BaseModel):
    items: list[DealPNLSnapshotRead]
