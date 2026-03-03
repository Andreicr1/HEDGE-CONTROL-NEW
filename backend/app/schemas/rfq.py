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
    recipient_id: str = Field(..., description="Recipient identifier", max_length=100)
    recipient_name: str = Field(..., description="Recipient name", max_length=200)
    channel: RFQInvitationChannel
    message_body: str = Field(
        ..., description="Exact message body sent", max_length=4000
    )
    provider_message_id: str = Field(
        ..., description="Provider message id", max_length=128
    )
    send_status: RFQInvitationStatus
    sent_at: datetime
    idempotency_key: str = Field(
        ..., description="Idempotency key for send", max_length=128
    )


class RFQInvitationRead(RFQInvitationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rfq_id: UUID
    rfq_number: str = Field(..., max_length=32)
    created_at: datetime


class RFQCreate(BaseModel):
    intent: RFQIntent
    commodity: str = Field(..., max_length=50)
    quantity_mt: float = Field(..., description="Quantity in metric tons (MT)")
    delivery_window_start: date
    delivery_window_end: date
    direction: RFQDirection
    order_id: UUID | None = Field(None, description="Referenced commercial order ID")
    buy_trade_id: UUID | None = Field(
        None, description="Referenced buy trade (RFQ id) for SPREAD"
    )
    sell_trade_id: UUID | None = Field(
        None, description="Referenced sell trade (RFQ id) for SPREAD"
    )
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
                raise ValueError(
                    "buy_trade_id and sell_trade_id are required for SPREAD"
                )
            if self.buy_trade_id == self.sell_trade_id:
                raise ValueError("buy_trade_id and sell_trade_id must be different")
        return self


class FloatPricingConvention(str, Enum):
    avg = "avg"
    avginter = "avginter"
    c2r = "c2r"


class RFQQuoteCreate(BaseModel):
    rfq_id: UUID
    counterparty_id: str = Field(..., max_length=100)
    fixed_price_value: float
    fixed_price_unit: str = Field(..., max_length=32)
    float_pricing_convention: FloatPricingConvention
    received_at: datetime


class RFQQuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rfq_id: UUID
    counterparty_id: str = Field(..., max_length=100)
    fixed_price_value: float
    fixed_price_unit: str = Field(..., max_length=32)
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
    counterparty_id: str = Field(..., max_length=100)
    spread_value: float
    buy_quote: RFQQuoteRead
    sell_quote: RFQQuoteRead


class SpreadRankingRead(BaseModel):
    rfq_id: UUID
    status: str = Field(..., max_length=32)
    failure_code: SpreadRankingFailureCode | None = None
    failure_reason: str | None = Field(None, max_length=500)
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
    status: str = Field(..., max_length=32)
    failure_code: TradeRankingFailureCode | None = None
    failure_reason: str | None = Field(None, max_length=500)
    ranking: list[TradeRankingEntry] = Field(default_factory=list)


class RFQUserActionBase(BaseModel):
    user_id: str = Field(..., max_length=100)


class RFQRejectRequest(RFQUserActionBase):
    pass


class RFQRefreshRequest(RFQUserActionBase):
    pass


class RFQAwardRequest(RFQUserActionBase):
    pass


class RFQRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rfq_number: str = Field(..., max_length=32)
    intent: RFQIntent
    commodity: str = Field(..., max_length=50)
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
    deleted_at: datetime | None = None
    invitations: list[RFQInvitationRead] = Field(default_factory=list)


class RFQListResponse(BaseModel):
    items: list[RFQRead]
    next_cursor: str | None = Field(None, max_length=256)


# ─────────────────────────────────────────────────────────────────────────────
# Preview-text (RFQ engine integration)
# ─────────────────────────────────────────────────────────────────────────────

class RFQPriceTypeEnum(str, Enum):
    avg = "AVG"
    avginter = "AVGInter"
    fix = "Fix"
    c2r = "C2R"


class RFQSideEnum(str, Enum):
    buy = "buy"
    sell = "sell"


class RFQTradeTypeEnum(str, Enum):
    swap = "Swap"
    forward = "Forward"


class RFQOrderTypeEnum(str, Enum):
    at_market = "At Market"
    limit = "Limit"
    range = "Range"
    resting = "Resting"


class RFQLegInput(BaseModel):
    side: RFQSideEnum
    price_type: RFQPriceTypeEnum
    quantity_mt: float = Field(..., gt=0)

    # AVG
    month_name: str | None = Field(None, max_length=20)
    year: int | None = None

    # AVGInter
    start_date: date | None = None
    end_date: date | None = None

    # Fix / C2R
    fixing_date: date | None = None

    # Order instruction (optional)
    order_type: RFQOrderTypeEnum | None = None
    order_validity: str | None = Field(None, max_length=30)
    order_limit_price: str | None = Field(None, max_length=30)


class RFQTextPreviewRequest(BaseModel):
    """Request body for the RFQ text preview endpoint."""
    trade_type: RFQTradeTypeEnum
    leg1: RFQLegInput
    leg2: RFQLegInput | None = None
    sync_ppt: bool = False
    company_header: str | None = Field(None, max_length=200)
    company_label_for_payoff: str = Field("Alcast", max_length=100)
    channel_type: str = Field("BROKER_LME", max_length=30)


class RFQTextPreviewResponse(BaseModel):
    """Response from the RFQ text preview endpoint."""
    text: str
    text_en: str = ""
    text_pt: str = ""
    leg1_ppt: date | None = None
    leg2_ppt: date | None = None
    trade_ppt: date | None = None
