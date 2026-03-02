"""Schemas for LLM Agent interactions."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class MessageIntent(str, Enum):
    quote = "QUOTE"
    rejection = "REJECTION"
    question = "QUESTION"
    other = "OTHER"


class ParsedQuote(BaseModel):
    """Structured output from the LLM parser.

    A ``confidence`` >= 0.85 indicates the LLM is sufficiently certain
    to auto-create a quote.  Below that threshold, human review is required.
    """

    intent: MessageIntent
    confidence: float = Field(..., ge=0.0, le=1.0)
    fixed_price_value: Decimal | None = None
    fixed_price_unit: str | None = Field(None, max_length=32)
    float_pricing_convention: str | None = Field(None, max_length=32)
    counterparty_name: str = Field(..., max_length=200)
    notes: str | None = Field(None, max_length=1000)


class LLMClassifyResult(BaseModel):
    """Result of intent classification."""

    intent: MessageIntent
    confidence: float = Field(..., ge=0.0, le=1.0)
    raw_reasoning: str | None = Field(None, max_length=2000)
