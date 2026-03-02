"""
Tests for the RFQ text engine, LME calendar, and message builder.

Covers:
- LME business-day calendar
- PPT computation for all PriceType variants
- Leg text generation (AVG, AVGInter, Fix, C2R)
- Pair override logic (Fix↔AVG, AVGInter↔Fix/C2R, Fix↔C2R, sync_ppt)
- Swap vs Forward full message assembly
- Execution instructions (Limit / Resting)
- Expected Payoff
- Validation
- Message builder (BANK / BROKER_LME channels)
- Preview-text API endpoint
"""

from datetime import date

import pytest

from app.services.lme_calendar import LMECalendar, add_business_days, second_business_day_of_next_month
from app.services.rfq_engine import (
    Leg,
    OrderInstruction,
    OrderType,
    PriceType,
    RfqTrade,
    Side,
    TradeType,
    ValidationError,
    build_execution_instruction,
    build_expected_payoff_text,
    build_leg_text,
    compute_ppt_for_leg,
    compute_trade_ppt_dates,
    fmt_date_short,
    fmt_qty,
    generate_rfq_text,
    validate_trade,
)
from app.services.rfq_message_builder import build_rfq_message


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cal() -> LMECalendar:
    """Calendar with no holidays (weekdays only) for deterministic tests."""
    return LMECalendar(holidays_iso=[])


def _cal_with_holidays() -> LMECalendar:
    """Calendar with a few test holidays."""
    return LMECalendar(holidays_iso=["2025-01-02", "2025-01-03"])


# ─────────────────────────────────────────────────────────────────────────────
# Calendar
# ─────────────────────────────────────────────────────────────────────────────

class TestLMECalendar:
    def test_weekday_is_business_day(self):
        cal = _cal()
        assert cal.is_business_day(date(2025, 1, 6))  # Monday

    def test_saturday_is_not_business_day(self):
        cal = _cal()
        assert not cal.is_business_day(date(2025, 1, 4))  # Saturday

    def test_sunday_is_not_business_day(self):
        cal = _cal()
        assert not cal.is_business_day(date(2025, 1, 5))  # Sunday

    def test_holiday_is_not_business_day(self):
        cal = _cal_with_holidays()
        assert not cal.is_business_day(date(2025, 1, 2))

    def test_add_business_days_simple(self):
        cal = _cal()
        # 2025-01-06 (Mon) + 2 biz days = 2025-01-08 (Wed)
        assert add_business_days(date(2025, 1, 6), 2, cal) == date(2025, 1, 8)

    def test_add_business_days_over_weekend(self):
        cal = _cal()
        # 2025-01-03 (Fri) + 2 biz days = 2025-01-07 (Tue)
        assert add_business_days(date(2025, 1, 3), 2, cal) == date(2025, 1, 7)

    def test_add_business_days_skips_holidays(self):
        cal = _cal_with_holidays()
        # 2025-01-01 (Wed) + 2 biz = skip Thu(2), Fri(3) → Mon(6), Tue(7) → 2025-01-07
        assert add_business_days(date(2025, 1, 1), 2, cal) == date(2025, 1, 7)

    def test_second_business_day_of_next_month_jan(self):
        cal = _cal()
        # Month 0 (Jan) → 2nd biz day of Feb: Feb 1 (Sat) skip, Feb 2 (Sun) skip,
        # Feb 3 (Mon) = 1st, Feb 4 (Tue) = 2nd
        result = second_business_day_of_next_month(2025, 0, cal)
        assert result == date(2025, 2, 4)

    def test_second_business_day_of_next_month_dec(self):
        cal = _cal()
        # Month 11 (Dec) → 2nd biz day of Jan (next year)
        # Jan 1 2026 = Thu(1st), Jan 2 = Fri(2nd)
        result = second_business_day_of_next_month(2025, 11, cal)
        assert result == date(2026, 1, 2)

    def test_add_holidays(self):
        cal = _cal()
        assert cal.is_business_day(date(2025, 6, 2))
        cal.add_holidays(["2025-06-02"])
        assert not cal.is_business_day(date(2025, 6, 2))


# ─────────────────────────────────────────────────────────────────────────────
# Formatting
# ─────────────────────────────────────────────────────────────────────────────

class TestFormatting:
    def test_fmt_date_short(self):
        assert fmt_date_short(date(2025, 1, 6)) == "06/01/25"

    def test_fmt_qty_integer(self):
        assert fmt_qty(10.0) == "10"
        assert fmt_qty(100) == "100"

    def test_fmt_qty_decimal(self):
        assert fmt_qty(10.5) == "10.5"
        assert fmt_qty(10.25) == "10.25"


# ─────────────────────────────────────────────────────────────────────────────
# PPT Computation
# ─────────────────────────────────────────────────────────────────────────────

class TestPPTComputation:
    def test_avg_ppt(self):
        cal = _cal()
        leg = Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                  month_name="January", year=2025)
        ppt = compute_ppt_for_leg(leg, cal)
        # 2nd biz day of Feb 2025
        assert ppt == date(2025, 2, 4)

    def test_avginter_ppt(self):
        cal = _cal()
        leg = Leg(side=Side.BUY, price_type=PriceType.AVG_INTER, quantity_mt=10,
                  start_date=date(2025, 1, 6), end_date=date(2025, 1, 31))
        ppt = compute_ppt_for_leg(leg, cal)
        # +2 biz days after Jan 31 (Fri) = Mon Feb 3, Tue Feb 4
        assert ppt == date(2025, 2, 4)

    def test_fix_ppt(self):
        cal = _cal()
        leg = Leg(side=Side.BUY, price_type=PriceType.FIX, quantity_mt=10,
                  fixing_date=date(2025, 1, 15))
        ppt = compute_ppt_for_leg(leg, cal)
        # +2 biz after Wed Jan 15 = Thu Jan 16, Fri Jan 17
        assert ppt == date(2025, 1, 17)

    def test_c2r_ppt(self):
        cal = _cal()
        leg = Leg(side=Side.BUY, price_type=PriceType.C2R, quantity_mt=10,
                  fixing_date=date(2025, 1, 15))
        ppt = compute_ppt_for_leg(leg, cal)
        assert ppt == date(2025, 1, 17)

    def test_ppt_override(self):
        cal = _cal()
        forced = date(2025, 3, 1)
        leg = Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                  month_name="January", year=2025, ppt=forced)
        assert compute_ppt_for_leg(leg, cal) == forced

    def test_avg_missing_fields_returns_none(self):
        cal = _cal()
        leg = Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10)
        assert compute_ppt_for_leg(leg, cal) is None

    def test_fix_no_fixing_date_returns_none(self):
        cal = _cal()
        leg = Leg(side=Side.BUY, price_type=PriceType.FIX, quantity_mt=10)
        assert compute_ppt_for_leg(leg, cal) is None


# ─────────────────────────────────────────────────────────────────────────────
# Leg text
# ─────────────────────────────────────────────────────────────────────────────

class TestLegText:
    def test_avg_leg(self):
        cal = _cal()
        leg = Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                  month_name="January", year=2025)
        text = build_leg_text(leg, cal)
        assert text == "Buy 10 mt Al AVG January 2025 Flat"

    def test_avginter_leg(self):
        cal = _cal()
        leg = Leg(side=Side.SELL, price_type=PriceType.AVG_INTER, quantity_mt=25,
                  start_date=date(2025, 1, 6), end_date=date(2025, 1, 31))
        text = build_leg_text(leg, cal)
        assert text.startswith("Sell 25 mt Al Fixing AVG 06/01/25 to 31/01/25")
        assert "ppt 04/02/25" in text

    def test_fix_leg_with_fixing_date(self):
        cal = _cal()
        leg = Leg(side=Side.BUY, price_type=PriceType.FIX, quantity_mt=10,
                  fixing_date=date(2025, 1, 15))
        text = build_leg_text(leg, cal)
        assert text == "Buy 10 mt Al USD ppt 17/01/25"

    def test_fix_leg_no_fixing_date(self):
        cal = _cal()
        leg = Leg(side=Side.BUY, price_type=PriceType.FIX, quantity_mt=10)
        text = build_leg_text(leg, cal)
        assert text == "Buy 10 mt Al USD"

    def test_c2r_leg(self):
        cal = _cal()
        leg = Leg(side=Side.SELL, price_type=PriceType.C2R, quantity_mt=10,
                  fixing_date=date(2025, 1, 15))
        text = build_leg_text(leg, cal)
        assert text == "Sell 10 mt Al C2R 15/01/25 ppt 17/01/25"


# ─────────────────────────────────────────────────────────────────────────────
# Execution instruction
# ─────────────────────────────────────────────────────────────────────────────

class TestExecutionInstruction:
    def test_limit_buy(self):
        order = OrderInstruction(order_type=OrderType.LIMIT, limit_price="2300")
        text = build_execution_instruction(order, Side.BUY)
        assert "Limit @ USD 2300" in text
        assert "valid for Day" in text

    def test_resting_buy(self):
        order = OrderInstruction(order_type=OrderType.RESTING)
        text = build_execution_instruction(order, Side.BUY)
        assert "best offer" in text
        assert "valid for Day" in text

    def test_resting_sell(self):
        order = OrderInstruction(order_type=OrderType.RESTING)
        text = build_execution_instruction(order, Side.SELL)
        assert "best bid" in text

    def test_custom_validity(self):
        order = OrderInstruction(order_type=OrderType.LIMIT, validity="GTC", limit_price="2400")
        text = build_execution_instruction(order, Side.BUY)
        assert "valid for GTC" in text


# ─────────────────────────────────────────────────────────────────────────────
# Expected Payoff
# ─────────────────────────────────────────────────────────────────────────────

class TestExpectedPayoff:
    def test_payoff_fix_vs_avg(self):
        cal = _cal()
        fixed = Leg(side=Side.BUY, price_type=PriceType.FIX, quantity_mt=10)
        avg = Leg(side=Side.SELL, price_type=PriceType.AVG, quantity_mt=10,
                  month_name="January", year=2025)
        text = build_expected_payoff_text(fixed, avg, cal)
        assert "Monthly Average of January 2025" in text
        assert "Alcast" in text

    def test_payoff_direction_buy_fixed(self):
        cal = _cal()
        fixed = Leg(side=Side.BUY, price_type=PriceType.FIX, quantity_mt=10)
        avg = Leg(side=Side.SELL, price_type=PriceType.AVG, quantity_mt=10,
                  month_name="March", year=2025)
        text = build_expected_payoff_text(fixed, avg, cal)
        # BUY fixed → pays_when_higher = False → receives_if_higher = True
        # Higher → receives, Lower → pays
        assert "Alcast receives the difference" in text

    def test_payoff_direction_sell_fixed(self):
        cal = _cal()
        fixed = Leg(side=Side.SELL, price_type=PriceType.FIX, quantity_mt=10)
        avg = Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                  month_name="March", year=2025)
        text = build_expected_payoff_text(fixed, avg, cal)
        # SELL fixed → pays_when_higher = True → receives_if_higher = False
        # Higher → pays, Lower → receives
        assert "Alcast pays the difference" in text


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestValidation:
    def test_valid_trade(self):
        trade = RfqTrade(
            trade_type=TradeType.SWAP,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
            leg2=Leg(side=Side.SELL, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="February", year=2025),
        )
        assert validate_trade(trade) == []

    def test_zero_qty(self):
        trade = RfqTrade(
            trade_type=TradeType.FORWARD,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=0,
                     month_name="January", year=2025),
        )
        errs = validate_trade(trade)
        assert len(errs) == 1
        assert errs[0].code == "qty_non_positive"

    def test_c2r_missing_fixing(self):
        trade = RfqTrade(
            trade_type=TradeType.FORWARD,
            leg1=Leg(side=Side.BUY, price_type=PriceType.C2R, quantity_mt=10),
        )
        errs = validate_trade(trade)
        assert any(e.code == "missing_fixing_date" for e in errs)

    def test_avginter_bad_range(self):
        trade = RfqTrade(
            trade_type=TradeType.FORWARD,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG_INTER, quantity_mt=10,
                     start_date=date(2025, 2, 1), end_date=date(2025, 1, 1)),
        )
        errs = validate_trade(trade)
        assert any(e.code == "avginter_bad_range" for e in errs)


# ─────────────────────────────────────────────────────────────────────────────
# Full message generation
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateRfqText:
    def test_swap_avg_avg(self):
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.SWAP,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
            leg2=Leg(side=Side.SELL, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="February", year=2025),
        )
        text = generate_rfq_text(trade, cal=cal)
        assert "How can I" in text
        assert "against?" in text
        assert "AVG January 2025 Flat" in text
        assert "AVG February 2025 Flat" in text

    def test_forward_single_leg(self):
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.FORWARD,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=25,
                     month_name="March", year=2025),
        )
        text = generate_rfq_text(trade, cal=cal)
        assert text == "How can I Buy 25 mt Al AVG March 2025 Flat?"

    def test_swap_fix_avg_ordering(self):
        """Fix/C2R leg should appear first in the Swap text."""
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.SWAP,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
            leg2=Leg(side=Side.SELL, price_type=PriceType.FIX, quantity_mt=10),
        )
        text = generate_rfq_text(trade, cal=cal)
        # Fix leg (leg2) should come first
        idx_fix = text.index("USD")
        idx_avg = text.index("AVG")
        assert idx_fix < idx_avg

    def test_swap_fix_c2r_official_settlement(self):
        """Fix paired with C2R should produce 'Official Settlement Price' wording."""
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.SWAP,
            leg1=Leg(side=Side.BUY, price_type=PriceType.FIX, quantity_mt=10),
            leg2=Leg(side=Side.SELL, price_type=PriceType.C2R, quantity_mt=10,
                     fixing_date=date(2025, 1, 15)),
        )
        text = generate_rfq_text(trade, cal=cal)
        assert "Official Settlement Price" in text

    def test_company_header(self):
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.FORWARD,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
        )
        text = generate_rfq_text(trade, cal=cal, company_header="Alcast Brasil")
        assert text.startswith("For Alcast Brasil Account:")

    def test_limit_order_instruction(self):
        cal = _cal()
        order = OrderInstruction(order_type=OrderType.LIMIT, limit_price="2300")
        trade = RfqTrade(
            trade_type=TradeType.SWAP,
            leg1=Leg(side=Side.BUY, price_type=PriceType.FIX, quantity_mt=10,
                     fixing_date=date(2025, 1, 15), order=order),
            leg2=Leg(side=Side.SELL, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
        )
        text = generate_rfq_text(trade, cal=cal)
        assert "Execution Instruction:" in text
        assert "Limit @ USD 2300" in text

    def test_resting_fix_no_fixing_appends_ppt(self):
        """Resting + Fix (no fixing_date) paired with AVG appends ppt to AVG leg."""
        cal = _cal()
        order = OrderInstruction(order_type=OrderType.RESTING)
        trade = RfqTrade(
            trade_type=TradeType.SWAP,
            leg1=Leg(side=Side.BUY, price_type=PriceType.FIX, quantity_mt=10,
                     order=order),
            leg2=Leg(side=Side.SELL, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
        )
        text = generate_rfq_text(trade, cal=cal)
        # The AVG leg text should get a ", ppt ..." appended because Fix has no fixing_date
        assert "ppt" in text

    def test_expected_payoff_in_swap_fix_avg(self):
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.SWAP,
            leg1=Leg(side=Side.BUY, price_type=PriceType.FIX, quantity_mt=10,
                     fixing_date=date(2025, 1, 15)),
            leg2=Leg(side=Side.SELL, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
        )
        text = generate_rfq_text(trade, cal=cal)
        assert "Expected Payoff:" in text

    def test_forward_sync_ppt(self):
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.FORWARD,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
            leg2=Leg(side=Side.SELL, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="February", year=2025),
            sync_ppt=True,
        )
        text = generate_rfq_text(trade, cal=cal)
        # Forward with sync_ppt and 2 legs → two "How can I" lines
        assert text.count("How can I") == 2

    def test_validation_error_raises(self):
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.FORWARD,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=0,
                     month_name="January", year=2025),
        )
        with pytest.raises(ValueError, match="greater than zero"):
            generate_rfq_text(trade, cal=cal)


# ─────────────────────────────────────────────────────────────────────────────
# Pair overrides — PPT date computation
# ─────────────────────────────────────────────────────────────────────────────

class TestPairOverrides:
    def test_fix_avg_pppts_synchronised(self):
        """Fix paired with AVG → Fix inherits AVG PPT."""
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.SWAP,
            leg1=Leg(side=Side.BUY, price_type=PriceType.FIX, quantity_mt=10,
                     fixing_date=date(2025, 1, 15)),
            leg2=Leg(side=Side.SELL, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
        )
        ppts = compute_trade_ppt_dates(trade, cal=cal)
        # Fix inherits AVG's PPT (2nd biz day Feb) → both should be same
        assert ppts["leg1_ppt"] == ppts["leg2_ppt"]

    def test_avginter_fix_inherits_end_date(self):
        """Fix paired with AVGInter → Fix inherits AVGInter end_date as fixing."""
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.SWAP,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG_INTER, quantity_mt=10,
                     start_date=date(2025, 1, 6), end_date=date(2025, 1, 31)),
            leg2=Leg(side=Side.SELL, price_type=PriceType.FIX, quantity_mt=10),
        )
        ppts = compute_trade_ppt_dates(trade, cal=cal)
        assert ppts["leg1_ppt"] is not None
        assert ppts["leg2_ppt"] is not None

    def test_fix_c2r_pppts_synchronised(self):
        """Fix paired with C2R → Fix inherits C2R PPT."""
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.SWAP,
            leg1=Leg(side=Side.BUY, price_type=PriceType.FIX, quantity_mt=10),
            leg2=Leg(side=Side.SELL, price_type=PriceType.C2R, quantity_mt=10,
                     fixing_date=date(2025, 1, 15)),
        )
        ppts = compute_trade_ppt_dates(trade, cal=cal)
        # Fix inherits C2R's PPT
        assert ppts["leg1_ppt"] == ppts["leg2_ppt"]

    def test_trade_ppt_is_max(self):
        """trade_ppt should be the max of available leg PPTs."""
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.SWAP,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
            leg2=Leg(side=Side.SELL, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="March", year=2025),
        )
        ppts = compute_trade_ppt_dates(trade, cal=cal)
        assert ppts["trade_ppt"] == max(ppts["leg1_ppt"], ppts["leg2_ppt"])


# ─────────────────────────────────────────────────────────────────────────────
# Message builder
# ─────────────────────────────────────────────────────────────────────────────

class TestMessageBuilder:
    def test_broker_lme_channel(self):
        cal = _cal()
        trade = RfqTrade(
            trade_type=TradeType.FORWARD,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
        )
        text = build_rfq_message("BROKER_LME", trade, cal=cal)
        assert "How can I" in text

    def test_bank_channel_portuguese(self):
        trade = RfqTrade(
            trade_type=TradeType.FORWARD,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
        )
        text = build_rfq_message("BANK", trade)
        assert "Bom dia" in text
        assert "Compra" in text
        assert "10 toneladas" in text
        assert "RFQ" in text

    def test_bank_sell_direction(self):
        trade = RfqTrade(
            trade_type=TradeType.FORWARD,
            leg1=Leg(side=Side.SELL, price_type=PriceType.AVG, quantity_mt=20,
                     month_name="February", year=2025),
        )
        text = build_rfq_message("BANK", trade)
        assert "Venda" in text

    def test_precomputed_text_passthrough(self):
        trade = RfqTrade(
            trade_type=TradeType.FORWARD,
            leg1=Leg(side=Side.BUY, price_type=PriceType.AVG, quantity_mt=10,
                     month_name="January", year=2025),
        )
        text = build_rfq_message("BROKER_LME", trade, precomputed_lme_text="PRECOMPUTED")
        assert text == "PRECOMPUTED"


# ─────────────────────────────────────────────────────────────────────────────
# Preview-text API endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestPreviewTextEndpoint:
    def test_preview_forward_avg(self, client):
        payload = {
            "trade_type": "Forward",
            "leg1": {
                "side": "buy",
                "price_type": "AVG",
                "quantity_mt": 25,
                "month_name": "January",
                "year": 2025,
            },
        }
        resp = client.post("/rfqs/preview-text", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert "How can I Buy 25 mt Al AVG January 2025 Flat?" in body["text"]
        assert body["leg1_ppt"] is not None

    def test_preview_swap_avg_avg(self, client):
        payload = {
            "trade_type": "Swap",
            "leg1": {
                "side": "buy",
                "price_type": "AVG",
                "quantity_mt": 10,
                "month_name": "January",
                "year": 2025,
            },
            "leg2": {
                "side": "sell",
                "price_type": "AVG",
                "quantity_mt": 10,
                "month_name": "February",
                "year": 2025,
            },
        }
        resp = client.post("/rfqs/preview-text", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert "against?" in body["text"]
        assert body["leg1_ppt"] is not None
        assert body["leg2_ppt"] is not None
        assert body["trade_ppt"] is not None

    def test_preview_bank_channel(self, client):
        payload = {
            "trade_type": "Forward",
            "channel_type": "BANK",
            "leg1": {
                "side": "buy",
                "price_type": "AVG",
                "quantity_mt": 10,
                "month_name": "January",
                "year": 2025,
            },
        }
        resp = client.post("/rfqs/preview-text", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert "Bom dia" in body["text"]

    def test_preview_with_company_header(self, client):
        payload = {
            "trade_type": "Forward",
            "company_header": "Alcast Brasil",
            "leg1": {
                "side": "buy",
                "price_type": "AVG",
                "quantity_mt": 10,
                "month_name": "March",
                "year": 2025,
            },
        }
        resp = client.post("/rfqs/preview-text", json=payload)
        assert resp.status_code == 200
        assert "For Alcast Brasil Account:" in resp.json()["text"]

    def test_preview_with_limit_order(self, client):
        payload = {
            "trade_type": "Swap",
            "leg1": {
                "side": "buy",
                "price_type": "Fix",
                "quantity_mt": 10,
                "fixing_date": "2025-01-15",
                "order_type": "Limit",
                "order_limit_price": "2300",
            },
            "leg2": {
                "side": "sell",
                "price_type": "AVG",
                "quantity_mt": 10,
                "month_name": "January",
                "year": 2025,
            },
        }
        resp = client.post("/rfqs/preview-text", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert "Execution Instruction:" in body["text"]
        assert "Limit @ USD 2300" in body["text"]

    def test_preview_validation_error(self, client):
        payload = {
            "trade_type": "Forward",
            "leg1": {
                "side": "buy",
                "price_type": "C2R",
                "quantity_mt": 10,
                # missing fixing_date → validation error in engine
            },
        }
        resp = client.post("/rfqs/preview-text", json=payload)
        assert resp.status_code == 422
        assert "fixing date" in resp.json()["detail"].lower()
