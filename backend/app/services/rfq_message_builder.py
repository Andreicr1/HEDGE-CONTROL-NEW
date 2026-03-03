"""
RFQ message builder — adapts domain-model objects into LME-formatted text.

Two channel families:

* **BANK** — Portuguese-language summary (the bank handles LME execution
  internally, so the message is informational).
* **BROKER_LME** / default — full LME technical text produced by
  ``rfq_engine.generate_rfq_text()``.

Usage::

    from app.services.rfq_message_builder import build_rfq_message
    from app.services.rfq_engine import RfqTrade, Leg, ...

    text = build_rfq_message(
        channel_type="BROKER_LME",
        trade=trade,
        company_header="Alcast Brasil",
    )
"""

from __future__ import annotations

from typing import Optional

from app.services.lme_calendar import LMECalendar, lme_calendar
from app.services.rfq_engine import (
    Leg,
    PriceType,
    RfqTrade,
    Side,
    TradeType,
    generate_rfq_text,
)


# ─────────────────────────────────────────────────────────────────────────────
# Bank message (Portuguese)
# ─────────────────────────────────────────────────────────────────────────────

PRICE_TYPE_PT = {
    PriceType.AVG: "Média Mensal LME",
    PriceType.AVG_INTER: "Média de Período",
    PriceType.FIX: "Preço Fixo",
    PriceType.C2R: "Cash-to-Ring",
}


def _fmt_leg_pt(leg: Leg) -> str:
    """Format a single leg description in Portuguese."""
    sentido = "Compra" if leg.side == Side.BUY else "Venda"
    qty = int(leg.quantity_mt) if float(int(leg.quantity_mt)) == float(leg.quantity_mt) else leg.quantity_mt
    tipo = PRICE_TYPE_PT.get(leg.price_type, str(leg.price_type))

    txt = f"{sentido} {qty} mt Al – {tipo}"

    if leg.price_type == PriceType.AVG and leg.month_name and leg.year is not None:
        txt += f" ({leg.month_name} {leg.year})"
    elif leg.price_type == PriceType.AVG_INTER and leg.start_date and leg.end_date:
        s = leg.start_date.strftime("%d/%m/%Y")
        e = leg.end_date.strftime("%d/%m/%Y")
        txt += f" ({s} a {e})"
    elif leg.price_type in (PriceType.FIX, PriceType.C2R) and leg.fixing_date:
        txt += f" (fixing {leg.fixing_date.strftime('%d/%m/%Y')})"

    return txt


def _build_bank_message(
    trade: RfqTrade,
    company_header: Optional[str] = None,
) -> str:
    """Human-friendly Portuguese text for bank counterparties."""
    header = company_header or "Alcast"

    lines = [
        "Bom dia,",
        "",
        f"Solicitação de cotação – {header}",
        f"Commodity: Alumínio LME",
        "",
    ]

    lines.append(_fmt_leg_pt(trade.leg1))

    if trade.leg2 is not None:
        lines.append(_fmt_leg_pt(trade.leg2))

    if trade.trade_type == TradeType.SWAP and trade.leg2 is not None:
        lines.append("")
        lines.append("Tipo: Swap (contra)")

    lines.extend(["", "Fico no aguardo da cotação.", "Att."])
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def build_rfq_message(
    channel_type: str,
    trade: RfqTrade,
    *,
    cal: Optional[LMECalendar] = None,
    company_header: Optional[str] = None,
    company_label_for_payoff: str = "Alcast",
    precomputed_lme_text: Optional[str] = None,
) -> str:
    """Build the RFQ message text appropriate for the given channel.

    Parameters
    ----------
    channel_type:
        Uppercase channel tag.  ``"BANK"`` triggers a Portuguese summary;
        anything else (``"BROKER_LME"``, ``"BROKER"``, ``"WHATSAPP"``, etc.)
        produces the full LME technical text.
    trade:
        Populated ``RfqTrade`` descriptor.
    cal:
        Optional LME calendar override.
    company_header:
        "For <header> Account:" line.
    company_label_for_payoff:
        Company name used in Expected Payoff.
    precomputed_lme_text:
        If the caller has already generated the LME text (e.g. from a
        preview endpoint), it is used as-is for non-BANK channels instead
        of regenerating.
    """
    ch = (channel_type or "BROKER_LME").upper()

    if ch == "BANK":
        return _build_bank_message(trade, company_header=company_header)

    # Default: full LME technical text
    if precomputed_lme_text:
        return precomputed_lme_text

    return generate_rfq_text(
        trade,
        cal=cal or lme_calendar(),
        company_header=company_header,
        company_label_for_payoff=company_label_for_payoff,
    )
