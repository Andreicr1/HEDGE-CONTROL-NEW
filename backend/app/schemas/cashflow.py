from datetime import date, datetime
from enum import Enum
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CashFlowView(str, Enum):
    analytic = "analytic"
    baseline = "baseline"
    ledger = "ledger"
    what_if = "what_if"


class CashFlowBase(BaseModel):
    contract_id: UUID = Field(..., description="Source contract ID")
    view: CashFlowView = Field(..., description="CashFlow view type")
    amount: float = Field(..., description="Derived cashflow amount")
    value_date: date = Field(..., description="Cashflow value date")


class CashFlowCreate(CashFlowBase):
    pass


class CashFlowRead(CashFlowBase):
    id: UUID
    created_at: datetime


class CashFlowItem(BaseModel):
    object_type: str
    object_id: str
    settlement_date: date
    amount_usd: Decimal
    mtm_value: Decimal


class CashFlowAnalyticResponse(BaseModel):
    as_of_date: date
    cashflow_items: list[CashFlowItem]
    total_net_cashflow: Decimal


class CashFlowBaselineSnapshotCreate(BaseModel):
    as_of_date: date
    correlation_id: str


class CashFlowBaselineSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    as_of_date: date
    snapshot_data: dict
    total_net_cashflow: Decimal
    created_at: datetime
    correlation_id: str


class LedgerLegId(str, Enum):
    fixed = "FIXED"
    float = "FLOAT"


class LedgerDirection(str, Enum):
    in_ = "IN"
    out = "OUT"


class HedgeContractSettlementLeg(BaseModel):
    leg_id: LedgerLegId
    direction: LedgerDirection
    amount: Decimal

    @model_validator(mode="after")
    def validate_amount(self) -> "HedgeContractSettlementLeg":
        if self.amount <= 0:
            raise ValueError("amount must be greater than zero")
        return self


class HedgeContractSettlementCreate(BaseModel):
    source_event_id: UUID
    cashflow_date: date
    currency: str | None = None
    legs: list[HedgeContractSettlementLeg]

    @model_validator(mode="after")
    def validate_payload(self) -> "HedgeContractSettlementCreate":
        if self.currency is not None and self.currency != "USD":
            raise ValueError("currency must be USD")
        if len(self.legs) != 2:
            raise ValueError("exactly two legs are required")
        leg_ids = {leg.leg_id for leg in self.legs}
        if leg_ids != {LedgerLegId.fixed, LedgerLegId.float}:
            raise ValueError("legs must include FIXED and FLOAT")
        return self


class LedgerEntriesQuery(BaseModel):
    source_event_type: str = Field("HEDGE_CONTRACT_SETTLED")
    source_event_id: UUID


class HedgeContractSettlementEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hedge_contract_id: UUID
    cashflow_date: date
    created_at: datetime


class CashFlowLedgerEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hedge_contract_id: UUID
    source_event_type: str
    source_event_id: UUID | None
    leg_id: str
    cashflow_date: date
    currency: str
    direction: str
    amount: Decimal
    created_at: datetime


class HedgeContractSettlementResponse(BaseModel):
    event: HedgeContractSettlementEventRead
    ledger_entries: list[CashFlowLedgerEntryRead]
