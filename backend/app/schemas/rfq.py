from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RFQIntent(str, Enum):
    commercial_hedge = "COMMERCIAL_HEDGE"
    global_position = "GLOBAL_POSITION"
    spread = "SPREAD"


class RFQDirection(str, Enum):
    buy = "BUY"
    sell = "SELL"


class RFQState(str, Enum):
    created = "CREATED"
    sent = "SENT"
    quoted = "QUOTED"
    awarded = "AWARDED"
    closed = "CLOSED"


class RFQInvitationChannel(str, Enum):
    email = "email"
    api = "api"
    whatsapp = "whatsapp"
    bank = "bank"
    broker = "broker"
    other = "other"


class RFQInvitationStatus(str, Enum):
    queued = "queued"
    sent = "sent"
    failed = "failed"


class RFQInvitationCreate(BaseModel):
    recipient_id: str = Field(..., description="Recipient identifier")
    recipient_name: str = Field(..., description="Recipient name")
    channel: RFQInvitationChannel
    message_body: str = Field(..., description="Exact message body sent")
    provider_message_id: str = Field(..., description="Provider message id")
    send_status: RFQInvitationStatus
    sent_at: datetime
    idempotency_key: str = Field(..., description="Idempotency key for send")


class RFQInvitationRead(RFQInvitationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rfq_id: UUID
    rfq_number: str
    created_at: datetime


class RFQCreate(BaseModel):
    intent: RFQIntent
    commodity: str
    quantity_mt: float = Field(..., description="Quantity in metric tons (MT)")
    delivery_window_start: date
    delivery_window_end: date
    direction: RFQDirection
    order_id: UUID | None = Field(None, description="Referenced commercial order ID")
    buy_trade_id: UUID | None = Field(None, description="Referenced buy trade (RFQ id) for SPREAD")
    sell_trade_id: UUID | None = Field(None, description="Referenced sell trade (RFQ id) for SPREAD")
    invitations: list[RFQInvitationCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_intent(self) -> "RFQCreate":
        if self.quantity_mt <= 0:
            raise ValueError("quantity_mt must be greater than zero")
        if self.intent == RFQIntent.commercial_hedge and self.order_id is None:
            raise ValueError("order_id is required for COMMERCIAL_HEDGE")
        if self.intent == RFQIntent.global_position and self.order_id is not None:
            raise ValueError("order_id must be empty for GLOBAL_POSITION")
        if self.intent == RFQIntent.spread:
            if self.order_id is not None:
                raise ValueError("order_id must be empty for SPREAD")
            if self.buy_trade_id is None or self.sell_trade_id is None:
                raise ValueError("buy_trade_id and sell_trade_id are required for SPREAD")
            if self.buy_trade_id == self.sell_trade_id:
                raise ValueError("buy_trade_id and sell_trade_id must be different")
        return self


class FloatPricingConvention(str, Enum):
    avg = "avg"
    avginter = "avginter"
    c2r = "c2r"


class RFQQuoteCreate(BaseModel):
    rfq_id: UUID
    counterparty_id: str
    fixed_price_value: float
    fixed_price_unit: str
    float_pricing_convention: FloatPricingConvention
    received_at: datetime


class RFQQuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rfq_id: UUID
    counterparty_id: str
    fixed_price_value: float
    fixed_price_unit: str
    float_pricing_convention: FloatPricingConvention
    received_at: datetime
    created_at: datetime


class SpreadRankingFailureCode(str, Enum):
    no_eligible_quotes = "NO_ELIGIBLE_QUOTES"
    non_comparable = "NON_COMPARABLE"
    tie = "TIE"
    not_spread_intent = "NOT_SPREAD_INTENT"


class SpreadRankingEntry(BaseModel):
    rank: int
    counterparty_id: str
    spread_value: float
    buy_quote: RFQQuoteRead
    sell_quote: RFQQuoteRead


class SpreadRankingRead(BaseModel):
    rfq_id: UUID
    status: str
    failure_code: SpreadRankingFailureCode | None = None
    failure_reason: str | None = None
    ranking: list[SpreadRankingEntry] = Field(default_factory=list)


class TradeRankingFailureCode(str, Enum):
    no_eligible_quotes = "NO_ELIGIBLE_QUOTES"
    non_comparable = "NON_COMPARABLE"
    tie = "TIE"
    not_trade_intent = "NOT_TRADE_INTENT"


class TradeRankingEntry(BaseModel):
    rank: int
    quote: RFQQuoteRead


class TradeRankingRead(BaseModel):
    rfq_id: UUID
    status: str
    failure_code: TradeRankingFailureCode | None = None
    failure_reason: str | None = None
    ranking: list[TradeRankingEntry] = Field(default_factory=list)


class RFQUserActionBase(BaseModel):
    user_id: str


class RFQRejectRequest(RFQUserActionBase):
    pass


class RFQRefreshRequest(RFQUserActionBase):
    pass


class RFQAwardRequest(RFQUserActionBase):
    pass


class RFQRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rfq_number: str
    intent: RFQIntent
    commodity: str
    quantity_mt: float
    delivery_window_start: date
    delivery_window_end: date
    direction: RFQDirection
    order_id: UUID | None
    buy_trade_id: UUID | None
    sell_trade_id: UUID | None
    commercial_active_mt: float
    commercial_passive_mt: float
    commercial_net_mt: float
    commercial_reduction_applied_mt: float
    exposure_snapshot_timestamp: datetime
    state: RFQState
    created_at: datetime
    invitations: list[RFQInvitationRead] = Field(default_factory=list)
