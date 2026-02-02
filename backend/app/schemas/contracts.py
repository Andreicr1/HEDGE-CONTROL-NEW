from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class HedgeLegSide(str, Enum):
    buy = "buy"
    sell = "sell"


class HedgeLegPriceType(str, Enum):
    fixed = "fixed"
    variable = "variable"


class HedgeClassification(str, Enum):
    long = "long"
    short = "short"


class HedgeLeg(BaseModel):
    side: HedgeLegSide = Field(..., description="Leg side (buy or sell)")
    price_type: HedgeLegPriceType = Field(..., description="Leg price type (fixed or variable)")


class HedgeContractCreate(BaseModel):
    commodity: str = Field(..., description="Commodity identifier")
    quantity_mt: float = Field(..., description="Quantity in metric tons (MT)")
    legs: list[HedgeLeg] = Field(..., description="Exactly two legs: one fixed, one variable")

    @model_validator(mode="after")
    def validate_structure(self) -> "HedgeContractCreate":
        if self.quantity_mt <= 0:
            raise ValueError("quantity_mt must be greater than zero")
        if len(self.legs) != 2:
            raise ValueError("hedge contract must have exactly two legs")
        fixed_legs = [leg for leg in self.legs if leg.price_type == HedgeLegPriceType.fixed]
        variable_legs = [leg for leg in self.legs if leg.price_type == HedgeLegPriceType.variable]
        if len(fixed_legs) != 1 or len(variable_legs) != 1:
            raise ValueError("hedge contract must have exactly one fixed leg and one variable leg")
        return self


class HedgeContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    commodity: str
    quantity_mt: float
    rfq_id: UUID | None = None
    rfq_quote_id: UUID | None = None
    counterparty_id: str | None = None
    fixed_price_value: float | None = None
    fixed_price_unit: str | None = None
    float_pricing_convention: str | None = None
    status: str | None = None
    fixed_leg_side: HedgeLegSide = Field(..., description="Fixed leg side (buy or sell)")
    variable_leg_side: HedgeLegSide = Field(..., description="Variable leg side (buy or sell)")
    classification: HedgeClassification = Field(..., description="Classification based on fixed leg")
    created_at: datetime
