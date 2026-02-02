from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class CashSettlementIngestRequest(BaseModel):
    settlement_date: date = Field(..., description="Settlement date to ingest (YYYY-MM-DD)")


class CashSettlementIngestResponse(BaseModel):
    ingested_count: int
    skipped_count: int
    source: str
    symbol: str
    settlement_date: date
    source_url: str
    html_sha256: str
    fetched_at: datetime


class CashSettlementPriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    symbol: str
    settlement_date: date
    price_usd: float
    source_url: str
    html_sha256: str
    fetched_at: datetime
    created_at: datetime

