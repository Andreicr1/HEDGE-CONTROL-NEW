"""Unit tests for rfq_message_builder — channel-aware RFQ text generation."""

from __future__ import annotations

from datetime import date

from app.services.rfq_engine import (
    Leg,
    PriceType,
    RfqTrade,
    Side,
    TradeType,
)
from app.services.rfq_message_builder import build_rfq_message


# ── helpers ──────────────────────────────────────────────────────────────


def _avg_buy_trade(qty: float = 100.0) -> RfqTrade:
    return RfqTrade(
        trade_type=TradeType.FORWARD,
        leg1=Leg(
            side=Side.BUY,
            price_type=PriceType.AVG,
            quantity_mt=qty,
            month_name="January",
            year=2026,
        ),
    )


def _avg_sell_trade(qty: float = 50.0) -> RfqTrade:
    return RfqTrade(
        trade_type=TradeType.FORWARD,
        leg1=Leg(
            side=Side.SELL,
            price_type=PriceType.AVG,
            quantity_mt=qty,
            month_name="March",
            year=2026,
        ),
    )


def _avginter_trade() -> RfqTrade:
    return RfqTrade(
        trade_type=TradeType.FORWARD,
        leg1=Leg(
            side=Side.BUY,
            price_type=PriceType.AVG_INTER,
            quantity_mt=75.0,
            start_date=date(2026, 1, 15),
            end_date=date(2026, 2, 15),
        ),
    )


def _fix_trade() -> RfqTrade:
    return RfqTrade(
        trade_type=TradeType.FORWARD,
        leg1=Leg(
            side=Side.SELL,
            price_type=PriceType.FIX,
            quantity_mt=25.0,
            fixing_date=date(2026, 3, 10),
        ),
    )


# ── BANK channel (Portuguese summary) ───────────────────────────────────


def test_bank_message_buy_side():
    text = build_rfq_message("BANK", _avg_buy_trade())
    assert "Bom dia" in text
    assert "Compra" in text
    assert "100 toneladas" in text
    assert "January 2026" in text


def test_bank_message_sell_side():
    text = build_rfq_message("BANK", _avg_sell_trade())
    assert "Venda" in text
    assert "50 toneladas" in text
    assert "March 2026" in text


def test_bank_message_company_header():
    text = build_rfq_message("BANK", _avg_buy_trade(), company_header="TestCorp")
    assert "TestCorp" in text


def test_bank_message_default_header():
    text = build_rfq_message("BANK", _avg_buy_trade())
    assert "Alcast" in text


def test_bank_message_avginter_period():
    text = build_rfq_message("BANK", _avginter_trade())
    assert "15/01/2026" in text
    assert "15/02/2026" in text


def test_bank_message_fix_period():
    text = build_rfq_message("BANK", _fix_trade())
    assert "10/03/2026" in text


def test_bank_message_fractional_qty():
    trade = RfqTrade(
        trade_type=TradeType.FORWARD,
        leg1=Leg(
            side=Side.BUY,
            price_type=PriceType.AVG,
            quantity_mt=10.5,
            month_name="May",
            year=2026,
        ),
    )
    text = build_rfq_message("BANK", trade)
    assert "10.5 toneladas" in text


def test_bank_message_integer_qty_no_decimal():
    trade = RfqTrade(
        trade_type=TradeType.FORWARD,
        leg1=Leg(
            side=Side.BUY,
            price_type=PriceType.AVG,
            quantity_mt=10.0,
            month_name="May",
            year=2026,
        ),
    )
    text = build_rfq_message("BANK", trade)
    # Integer quantity should not show ".0"
    assert "10 toneladas" in text


# ── BROKER_LME channel (full LME text) ──────────────────────────────────


def test_broker_lme_generates_lme_text():
    text = build_rfq_message("BROKER_LME", _avg_buy_trade())
    # Should contain LME-formatted text (not Portuguese summary)
    assert "Bom dia" not in text
    assert len(text) > 0


def test_broker_channel_same_as_broker_lme():
    t = _avg_buy_trade()
    lme = build_rfq_message("BROKER_LME", t)
    broker = build_rfq_message("BROKER", t)
    assert lme == broker


def test_empty_channel_defaults_to_broker_lme():
    t = _avg_buy_trade()
    default = build_rfq_message("", t)
    explicit = build_rfq_message("BROKER_LME", t)
    assert default == explicit


def test_none_channel_defaults_to_broker_lme():
    t = _avg_buy_trade()
    default = build_rfq_message(None, t)
    explicit = build_rfq_message("BROKER_LME", t)
    assert default == explicit


def test_precomputed_text_used_for_broker():
    text = build_rfq_message(
        "BROKER_LME",
        _avg_buy_trade(),
        precomputed_lme_text="PRE-COMPUTED TEXT",
    )
    assert text == "PRE-COMPUTED TEXT"


def test_precomputed_text_ignored_for_bank():
    text = build_rfq_message(
        "BANK",
        _avg_buy_trade(),
        precomputed_lme_text="PRE-COMPUTED TEXT",
    )
    assert text != "PRE-COMPUTED TEXT"
    assert "Bom dia" in text


def test_company_header_for_lme_text():
    text = build_rfq_message(
        "BROKER_LME",
        _avg_buy_trade(),
        company_header="TestCorp",
    )
    assert "TestCorp" in text


def test_case_insensitive_bank_channel():
    text = build_rfq_message("bank", _avg_buy_trade())
    assert "Bom dia" in text


def test_whatsapp_channel_uses_lme_format():
    text = build_rfq_message("WHATSAPP", _avg_buy_trade())
    assert "Bom dia" not in text
    assert len(text) > 0
