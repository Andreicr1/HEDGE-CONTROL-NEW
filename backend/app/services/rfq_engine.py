"""
Pure-Python RFQ text engine – LME aluminium hedging messages.

Ported from the legacy Hedge-Control ``rfq_engine.py`` (Andreicr1/RFQ-Generator).

Design goals
────────────
* Deterministic, side-effect-free message generation.
* Backend-friendly: no UI/DOM assumptions.
* Output strings match the LME "dialect" (punctuation, ordering, line breaks)
  accepted by brokers and banks.

Key LME conventions mirrored
─────────────────────────────
* Swap vs Forward wording
* Fixed-leg ordering preference in Swap ("Fix/C2R first" when paired with
  AVG/AVGInter)
* Special formatting for Fix vs C2R ("Official Settlement Price of …")
* PPT rules:
    - AVG  → 2nd business day of next month
    - AVGInter → +2 biz days after ``end_date``
    - Fix/C2R  → +2 biz days after ``fixing_date`` (unless overridden by
      pairing logic)
* Execution Instruction for Limit / Resting orders
* Expected Payoff text — pay/receive direction based on fixed-leg side
* Resting + Fix (no fixing_date) paired with AVG adds ", ppt <date>" to AVG
  leg

Changes from legacy
───────────────────
* Calendar functions imported from ``lme_calendar`` module (no duplication).
* ``_compute_pair_overrides`` extracted as a top-level helper — called once
  from both ``generate_rfq_text`` and ``compute_trade_ppt_dates``
  (was duplicated in the legacy code).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict, List, Optional, Tuple

from app.services.lme_calendar import (
    LMECalendar,
    add_business_days,
    lme_calendar,
    second_business_day_of_next_month,
)


# ─────────────────────────────────────────────────────────────────────────────
# Enums / Data Models
# ─────────────────────────────────────────────────────────────────────────────

class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"

    def verb(self) -> str:
        return "Buy" if self == Side.BUY else "Sell"


class PriceType(str, Enum):
    AVG = "AVG"
    AVG_INTER = "AVGInter"
    FIX = "Fix"
    C2R = "C2R"


class TradeType(str, Enum):
    SWAP = "Swap"
    FORWARD = "Forward"


class OrderType(str, Enum):
    AT_MARKET = "At Market"
    LIMIT = "Limit"
    RANGE = "Range"        # reserved
    RESTING = "Resting"


@dataclass(frozen=True)
class OrderInstruction:
    order_type: OrderType
    validity: Optional[str] = None      # e.g. "Day", "GTC", "3 Hours"
    limit_price: Optional[str] = None   # string to preserve formatting


@dataclass(frozen=True)
class Leg:
    side: Side
    price_type: PriceType
    quantity_mt: float

    # AVG fields
    month_name: Optional[str] = None   # e.g. "January"
    year: Optional[int] = None         # e.g. 2025

    # AVGInter fields
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # Fix / C2R fields
    fixing_date: Optional[date] = None

    # Computed / overridden PPT (caller override takes precedence)
    ppt: Optional[date] = None

    # Optional order instruction (relevant for Fix/C2R legs)
    order: Optional[OrderInstruction] = None


@dataclass(frozen=True)
class RfqTrade:
    trade_type: TradeType
    leg1: Leg
    leg2: Optional[Leg] = None   # None for single-leg Forward
    sync_ppt: bool = False       # Forward + sync_ppt generates two lines


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str


# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

MONTHS_EN = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_INDEX: Dict[str, int] = {m: i for i, m in enumerate(MONTHS_EN)}


def fmt_date_short(d: date) -> str:
    """Legacy format: DD/MM/YY."""
    return d.strftime("%d/%m/%y")


def fmt_qty(qty: float) -> str:
    """Format quantity — integers without ".0", decimals trimmed."""
    if float(int(qty)) == float(qty):
        return str(int(qty))
    return f"{qty:.10f}".rstrip("0").rstrip(".")


# ─────────────────────────────────────────────────────────────────────────────
# PPT computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_ppt_for_leg(leg: Leg, cal: LMECalendar) -> Optional[date]:
    """Compute the PPT (Prompt Payment Terms) settlement date for a single leg.

    Rules
    -----
    * AVG      → 2nd business day of next month
    * AVGInter → +2 business days after ``end_date``
    * Fix/C2R  → +2 business days after ``fixing_date``
    """
    if leg.ppt is not None:
        return leg.ppt

    if leg.price_type == PriceType.AVG:
        if leg.month_name is None or leg.year is None:
            return None
        idx = MONTH_INDEX.get(leg.month_name)
        if idx is None:
            return None
        return second_business_day_of_next_month(leg.year, idx, cal)

    if leg.price_type == PriceType.AVG_INTER:
        if leg.end_date is None:
            return None
        return add_business_days(leg.end_date, 2, cal)

    if leg.price_type in (PriceType.FIX, PriceType.C2R):
        if leg.fixing_date is None:
            return None
        return add_business_days(leg.fixing_date, 2, cal)

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Pair override logic (extracted — was duplicated in legacy)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_pair_overrides(
    leg_a: Leg,
    leg_b: Optional[Leg],
    cal: LMECalendar,
    sync_ppt: bool,
) -> Tuple[Leg, Optional[Leg]]:
    """Adjust fixing-date / PPT on paired legs according to LME conventions.

    This function encodes the following coupling rules:

    1. **AVGInter paired with Fix/C2R** → Fix/C2R leg inherits the AVGInter
       ``end_date`` as its fixing date.  If ``sync_ppt`` is set the PPT is
       also synchronised.
    2. **Fix paired with AVG** → the Fix leg drops its own fixing date and
       inherits the AVG leg's PPT (2nd biz day of next month).
    3. **Fix paired with C2R** → the Fix leg inherits the C2R PPT.
    4. **sync_ppt + AVGInter** → the other leg's PPT is overridden by the
       AVGInter PPT.
    """
    if leg_b is None:
        return leg_a, None

    a, b = leg_a, leg_b

    ppt_a = compute_ppt_for_leg(a, cal)
    ppt_b = compute_ppt_for_leg(b, cal)

    # --- AVGInter ↔ Fix/C2R ---
    if a.price_type == PriceType.AVG_INTER and b.price_type in (PriceType.FIX, PriceType.C2R) and a.end_date:
        b_fix = a.end_date
        b_ppt = ppt_a if sync_ppt else ppt_b
        b = Leg(**{**b.__dict__, "fixing_date": b_fix, "ppt": b_ppt})
        ppt_b = b_ppt
    if b.price_type == PriceType.AVG_INTER and a.price_type in (PriceType.FIX, PriceType.C2R) and b.end_date:
        a_fix = b.end_date
        a_ppt = ppt_b if sync_ppt else ppt_a
        a = Leg(**{**a.__dict__, "fixing_date": a_fix, "ppt": a_ppt})
        ppt_a = a_ppt

    # --- Fix ↔ AVG ---
    if a.price_type == PriceType.FIX and b.price_type == PriceType.AVG:
        a = Leg(**{**a.__dict__, "ppt": ppt_b, "fixing_date": None})
        ppt_a = ppt_b
    if b.price_type == PriceType.FIX and a.price_type == PriceType.AVG:
        b = Leg(**{**b.__dict__, "ppt": ppt_a, "fixing_date": None})
        ppt_b = ppt_a

    # --- Fix ↔ C2R ---
    if a.price_type == PriceType.FIX and b.price_type == PriceType.C2R:
        a = Leg(**{**a.__dict__, "ppt": ppt_b, "fixing_date": None})
        ppt_a = ppt_b
    if b.price_type == PriceType.FIX and a.price_type == PriceType.C2R:
        b = Leg(**{**b.__dict__, "ppt": ppt_a, "fixing_date": None})
        ppt_b = ppt_a

    # --- sync_ppt + AVGInter ---
    if sync_ppt and a.price_type == PriceType.AVG_INTER:
        b = Leg(**{**b.__dict__, "ppt": ppt_a})
    if sync_ppt and b.price_type == PriceType.AVG_INTER:
        a = Leg(**{**a.__dict__, "ppt": compute_ppt_for_leg(b, cal)})

    return a, b


# ─────────────────────────────────────────────────────────────────────────────
# Leg text
# ─────────────────────────────────────────────────────────────────────────────

def build_leg_text(leg: Leg, cal: LMECalendar) -> str:
    """Build the single-leg text fragment used inside the RFQ message."""
    s = leg.side.verb()
    qty = fmt_qty(leg.quantity_mt)
    txt = f"{s} {qty} mt Al "

    ppt = compute_ppt_for_leg(leg, cal)
    ppt_str = fmt_date_short(ppt) if ppt else ""

    if leg.price_type == PriceType.AVG:
        if not leg.month_name or leg.year is None:
            return (txt + "AVG").strip()
        txt += f"AVG {leg.month_name} {leg.year} Flat"
        return txt

    if leg.price_type == PriceType.AVG_INTER:
        if not leg.start_date or not leg.end_date:
            return (txt + "Fixing AVG").strip()
        ss = fmt_date_short(leg.start_date)
        ee = fmt_date_short(leg.end_date)
        txt += f"Fixing AVG {ss} to {ee}"
        if ppt_str:
            txt += f", ppt {ppt_str}"
        return txt

    if leg.price_type == PriceType.FIX:
        txt += "USD"
        if ppt_str:
            txt += f" ppt {ppt_str}"
        return txt

    if leg.price_type == PriceType.C2R:
        if leg.fixing_date is None:
            return (txt + "C2R").strip()
        f = fmt_date_short(leg.fixing_date)
        p = ppt_str or fmt_date_short(add_business_days(leg.fixing_date, 2, cal))
        txt += f"C2R {f} ppt {p}"
        return txt

    return txt.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Execution Instruction (Limit / Resting)
# ─────────────────────────────────────────────────────────────────────────────

def build_execution_instruction(order: OrderInstruction, side: Side) -> str:
    """Build execution-instruction line for Limit / Resting order types."""
    validity = order.validity or "Day"

    if order.order_type == OrderType.LIMIT:
        price = (order.limit_price or "").strip()
        return (
            f"Please work this order as a Limit @ USD {price} "
            f"for the Fixed price, valid for {validity}."
        )

    if order.order_type == OrderType.RESTING:
        # Legacy behaviour: flips bid/offer relative to side
        best = "best offer" if side == Side.BUY else "best bid"
        return (
            f"Please work this order posting as the {best} in the book "
            f"for the fixed price, valid for {validity}."
        )

    return f"Please work this order, valid for {validity}."


# ─────────────────────────────────────────────────────────────────────────────
# Expected Payoff
# ─────────────────────────────────────────────────────────────────────────────

def build_expected_payoff_text(
    fixed_leg: Leg,
    other_leg: Optional[Leg],
    cal: LMECalendar,
    company_label: str = "Alcast",
) -> str:
    """Build the Expected Payoff paragraph appended to certain RFQ messages."""
    pays_when_higher = fixed_leg.side == Side.SELL
    receives_if_higher = not pays_when_higher

    def _pays_or_receives(is_higher: bool) -> str:
        if is_higher:
            return "receives" if receives_if_higher else "pays"
        return "pays" if receives_if_higher else "receives"

    # --- Floating leg is AVG / AVGInter ---
    if other_leg is not None and other_leg.price_type in (PriceType.AVG, PriceType.AVG_INTER):
        if other_leg.price_type == PriceType.AVG and other_leg.month_name and other_leg.year is not None:
            month_year = f"{other_leg.month_name} {other_leg.year}"
        elif other_leg.price_type == PriceType.AVG_INTER and other_leg.end_date:
            month_year = f"{MONTHS_EN[other_leg.end_date.month - 1]} {other_leg.end_date.year}"
        else:
            month_year = "the relevant month"

        return (
            "Expected Payoff:\n"
            f"If official Monthly Average of {month_year} is higher than the Fixed Price, "
            f"{company_label} {_pays_or_receives(True)} the difference. "
            f"If the average is lower, {company_label} {_pays_or_receives(False)} the difference."
        )

    # --- Floating leg is C2R or single-leg Fix ---
    official_date: Optional[date] = None
    if other_leg is not None and other_leg.price_type == PriceType.C2R and other_leg.fixing_date:
        official_date = other_leg.fixing_date
    elif fixed_leg.fixing_date:
        official_date = fixed_leg.fixing_date

    official_str = fmt_date_short(official_date) if official_date else "the relevant date"

    return (
        "Expected Payoff:\n"
        f"If the official price of {official_str} is higher than the Fixed Price, "
        f"{company_label} {_pays_or_receives(True)} the difference. "
        f"If the official price is lower, {company_label} {_pays_or_receives(False)} the difference."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_trade(trade: RfqTrade) -> List[ValidationError]:
    """Validate trade legs, returning a list of errors (empty = valid)."""
    errs: List[ValidationError] = []

    def _check_leg(leg: Leg, idx: int) -> None:
        if leg.quantity_mt is None or not isinstance(leg.quantity_mt, (int, float)):
            errs.append(ValidationError("qty_invalid", f"Leg {idx}: Please enter a valid quantity."))
            return
        if leg.quantity_mt <= 0:
            errs.append(ValidationError("qty_non_positive", f"Leg {idx}: Quantity must be greater than zero."))

        if leg.price_type == PriceType.C2R and leg.fixing_date is None:
            errs.append(ValidationError("missing_fixing_date", "Please provide a fixing date."))

        if leg.price_type == PriceType.AVG:
            if not leg.month_name or leg.year is None:
                errs.append(ValidationError("avg_missing_month_year", f"Leg {idx}: AVG requires month/year."))

        if leg.price_type == PriceType.AVG_INTER:
            if not leg.start_date or not leg.end_date:
                errs.append(ValidationError("avginter_missing_dates", f"Leg {idx}: AVGInter requires start/end."))
            elif leg.start_date > leg.end_date:
                errs.append(ValidationError("avginter_bad_range", f"Leg {idx}: Start date must be <= end date."))

    _check_leg(trade.leg1, 1)
    if trade.leg2 is not None:
        _check_leg(trade.leg2, 2)

    return errs


# ─────────────────────────────────────────────────────────────────────────────
# Core RFQ message builder
# ─────────────────────────────────────────────────────────────────────────────

def generate_rfq_text(
    trade: RfqTrade,
    cal: Optional[LMECalendar] = None,
    company_header: Optional[str] = None,
    company_label_for_payoff: str = "Alcast",
) -> str:
    """Generate the full RFQ message text for an ``RfqTrade``.

    Parameters
    ----------
    trade:
        Fully-populated trade descriptor.
    cal:
        LME business-day calendar.  Falls back to the module singleton.
    company_header:
        When set, prepends "For <header> Account:\\n" to the text.
    company_label_for_payoff:
        Company name used in the Expected Payoff paragraph.

    Returns
    -------
    str
        Multi-line RFQ text ready for sending via WhatsApp / e-mail.
    """
    cal = cal or lme_calendar()

    errs = validate_trade(trade)
    if errs:
        raise ValueError(errs[0].message)

    l1 = trade.leg1
    l2 = trade.leg2

    # Apply pairing overrides (Fix↔AVG, AVGInter↔Fix, etc.)
    l1_adj, l2_adj = _compute_pair_overrides(l1, l2, cal, trade.sync_ppt)

    # Build individual leg texts
    leg1_text = build_leg_text(l1_adj, cal)
    leg2_text = build_leg_text(l2_adj, cal) if l2_adj else None

    # ── Swap special: "Official Settlement Price" wording for Fix↔C2R ──
    if trade.trade_type == TradeType.SWAP and l2_adj is not None:
        if l1_adj.price_type == PriceType.FIX and l2_adj.price_type == PriceType.C2R:
            f = fmt_date_short(l2_adj.fixing_date) if l2_adj.fixing_date else ""
            ppt2 = compute_ppt_for_leg(l2_adj, cal)
            ppt2s = fmt_date_short(ppt2) if ppt2 else ""
            leg2_text = (
                f"{l2_adj.side.verb()} {fmt_qty(l2_adj.quantity_mt)} mt Al "
                f"Official Settlement Price of {f}, PPT {ppt2s}"
            )
        elif l1_adj.price_type == PriceType.C2R and l2_adj.price_type == PriceType.FIX:
            f = fmt_date_short(l1_adj.fixing_date) if l1_adj.fixing_date else ""
            ppt1 = compute_ppt_for_leg(l1_adj, cal)
            ppt1s = fmt_date_short(ppt1) if ppt1 else ""
            leg1_text = (
                f"{l1_adj.side.verb()} {fmt_qty(l1_adj.quantity_mt)} mt Al "
                f"Official Settlement Price of {f}, PPT {ppt1s}"
            )

    # ── Resting + Fix (no fixing_date) paired with AVG → append ppt ──
    if l2_adj is not None:
        if (
            l1_adj.price_type == PriceType.FIX
            and l1_adj.order
            and l1_adj.order.order_type == OrderType.RESTING
            and l1_adj.fixing_date is None
            and l2_adj.price_type == PriceType.AVG
        ):
            ppt1 = compute_ppt_for_leg(l1_adj, cal)
            if ppt1:
                leg2_text = (leg2_text or "") + f", ppt {fmt_date_short(ppt1)}"
        if (
            l2_adj.price_type == PriceType.FIX
            and l2_adj.order
            and l2_adj.order.order_type == OrderType.RESTING
            and l2_adj.fixing_date is None
            and l1_adj.price_type == PriceType.AVG
        ):
            ppt2 = compute_ppt_for_leg(l2_adj, cal)
            if ppt2:
                leg1_text = (leg1_text or "") + f", ppt {fmt_date_short(ppt2)}"

    # ── Assemble the "How can I …?" text ──
    text: str

    if trade.trade_type == TradeType.FORWARD and trade.sync_ppt and l2_adj is not None:
        text = f"How can I {leg1_text}?\nHow can I {leg2_text}?"
    elif trade.trade_type == TradeType.FORWARD and l2_adj is None:
        text = f"How can I {leg1_text}?"
    elif trade.trade_type == TradeType.FORWARD and l2_adj is not None and l2_adj.price_type is None:
        text = f"How can I {leg1_text}?"
    else:
        # Swap — determine leg ordering (Fix/C2R first)
        assert l2_adj is not None and leg2_text is not None

        fix_types = {PriceType.FIX, PriceType.C2R}

        if l1_adj.price_type == PriceType.FIX and l2_adj.price_type == PriceType.C2R:
            text = f"How can I {leg1_text} and {leg2_text} against?"
        elif l1_adj.price_type == PriceType.C2R and l2_adj.price_type == PriceType.FIX:
            text = f"How can I {leg2_text} and {leg1_text} against?"
        elif l1_adj.price_type in fix_types and l2_adj.price_type not in fix_types:
            text = f"How can I {leg1_text} and {leg2_text} against?"
        elif l2_adj.price_type in fix_types and l1_adj.price_type not in fix_types:
            text = f"How can I {leg2_text} and {leg1_text} against?"
        else:
            text = f"How can I {leg1_text} and {leg2_text} against?"

    # ── Execution instruction ──
    exec_line: Optional[str] = None
    if l1_adj.order and l1_adj.order.order_type in (OrderType.LIMIT, OrderType.RESTING):
        exec_line = build_execution_instruction(
            OrderInstruction(
                order_type=l1_adj.order.order_type,
                validity=l1_adj.order.validity or "Day",
                limit_price=l1_adj.order.limit_price,
            ),
            l1_adj.side,
        )
    elif l2_adj and l2_adj.order and l2_adj.order.order_type in (OrderType.LIMIT, OrderType.RESTING):
        exec_line = build_execution_instruction(
            OrderInstruction(
                order_type=l2_adj.order.order_type,
                validity=l2_adj.order.validity or "Day",
                limit_price=l2_adj.order.limit_price,
            ),
            l2_adj.side,
        )

    if exec_line:
        text += f"\nExecution Instruction: {exec_line}"

    # ── Expected Payoff ──
    payoff: Optional[str] = None
    if l2_adj is None:
        if l1_adj.price_type == PriceType.FIX and l1_adj.fixing_date:
            payoff = build_expected_payoff_text(
                fixed_leg=l1_adj, other_leg=None,
                cal=cal, company_label=company_label_for_payoff,
            )
    else:
        if l1_adj.price_type in (PriceType.FIX, PriceType.C2R) and l2_adj.price_type in (PriceType.AVG, PriceType.AVG_INTER):
            payoff = build_expected_payoff_text(
                fixed_leg=l1_adj, other_leg=l2_adj,
                cal=cal, company_label=company_label_for_payoff,
            )
        elif l2_adj.price_type in (PriceType.FIX, PriceType.C2R) and l1_adj.price_type in (PriceType.AVG, PriceType.AVG_INTER):
            payoff = build_expected_payoff_text(
                fixed_leg=l2_adj, other_leg=l1_adj,
                cal=cal, company_label=company_label_for_payoff,
            )
        elif l1_adj.price_type == PriceType.FIX and l2_adj.price_type == PriceType.C2R:
            payoff = build_expected_payoff_text(
                fixed_leg=l1_adj, other_leg=l2_adj,
                cal=cal, company_label=company_label_for_payoff,
            )
        elif l1_adj.price_type == PriceType.C2R and l2_adj.price_type == PriceType.FIX:
            payoff = build_expected_payoff_text(
                fixed_leg=l2_adj, other_leg=l1_adj,
                cal=cal, company_label=company_label_for_payoff,
            )

    if payoff:
        text += f"\n{payoff}"

    # ── Company header ──
    if company_header:
        text = f"For {company_header} Account:\n{text}"

    return text


# ─────────────────────────────────────────────────────────────────────────────
# PPT date computation (public API)
# ─────────────────────────────────────────────────────────────────────────────

def compute_trade_ppt_dates(
    trade: RfqTrade,
    cal: Optional[LMECalendar] = None,
) -> dict:
    """Compute PPT (settlement) dates for a trade.

    Uses the same pairing / override rules as ``generate_rfq_text``.

    Returns
    -------
    dict
        ``{"leg1_ppt": date|None, "leg2_ppt": date|None, "trade_ppt": date|None}``
        where ``trade_ppt`` is ``max(available leg PPTs)``.
    """
    cal = cal or lme_calendar()

    errs = validate_trade(trade)
    if errs:
        raise ValueError(errs[0].message)

    l1_adj, l2_adj = _compute_pair_overrides(
        trade.leg1, trade.leg2, cal, trade.sync_ppt,
    )
    ppt1 = compute_ppt_for_leg(l1_adj, cal)
    ppt2 = compute_ppt_for_leg(l2_adj, cal) if l2_adj else None

    pts = [d for d in (ppt1, ppt2) if d is not None]
    trade_ppt = max(pts) if pts else None
    return {"leg1_ppt": ppt1, "leg2_ppt": ppt2, "trade_ppt": trade_ppt}
