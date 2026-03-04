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

_MONTH_PT = {
    "January": "Janeiro",
    "February": "Fevereiro",
    "March": "Março",
    "April": "Abril",
    "May": "Maio",
    "June": "Junho",
    "July": "Julho",
    "August": "Agosto",
    "September": "Setembro",
    "October": "Outubro",
    "November": "Novembro",
    "December": "Dezembro",
}

_PRICE_TYPE_PT = {
    PriceType.AVG: "Média",
    PriceType.AVG_INTER: "Média Período",
    PriceType.FIX: "Fix",
    PriceType.C2R: "C2R",
}


def _build_bank_message(
    trade: RfqTrade,
    company_header: Optional[str] = None,
) -> str:
    """Human-friendly Portuguese text for bank counterparties.

    Banks execute the LME trade on behalf of the client.  The message is a
    high-level summary rather than the technical "How can I …" wording.
    """
    leg = trade.leg1
    sentido = "Compra" if leg.side == Side.BUY else "Venda"
    qty = (
        int(leg.quantity_mt)
        if float(int(leg.quantity_mt)) == float(leg.quantity_mt)
        else leg.quantity_mt
    )

    # Derive period label
    if leg.price_type == PriceType.AVG and leg.month_name and leg.year is not None:
        periodo = f"{leg.month_name} {leg.year}"
    elif leg.price_type == PriceType.AVG_INTER and leg.start_date and leg.end_date:
        periodo = f"{leg.start_date.strftime('%d/%m/%Y')} a {leg.end_date.strftime('%d/%m/%Y')}"
    elif leg.fixing_date:
        periodo = leg.fixing_date.strftime("%d/%m/%Y")
    else:
        periodo = "conforme especificação"

    header = company_header or "Alcast"
    lines = [
        "Bom dia,",
        "",
        f"RFQ – {header}",
        "",
        f"{sentido}: {qty} toneladas de alumínio LME",
        "Preço: conforme condições técnicas LME, com média mensal (Monthly Average) "
        "e datas conforme especificação do RFQ",
        "",
        f"Período: {periodo}",
        "",
        "Fico no aguardo da cotação.",
    ]
    return "\n".join(lines)


def _leg_summary_pt(leg: Leg) -> str:
    """Build a one-segment Portuguese summary for a single leg."""
    sentido = "Compra" if leg.side == Side.BUY else "Vende"
    tipo = _PRICE_TYPE_PT.get(leg.price_type, str(leg.price_type.value))

    qty = (
        int(leg.quantity_mt)
        if float(int(leg.quantity_mt)) == float(leg.quantity_mt)
        else leg.quantity_mt
    )
    qty_str = f"{qty}T"

    if leg.price_type == PriceType.AVG and leg.month_name and leg.year is not None:
        month_pt = _MONTH_PT.get(leg.month_name, leg.month_name)
        return f"{sentido} {qty_str} - {tipo} {month_pt} {leg.year}"
    elif leg.price_type == PriceType.AVG_INTER and leg.start_date and leg.end_date:
        s = leg.start_date.strftime("%d/%m/%Y")
        e = leg.end_date.strftime("%d/%m/%Y")
        return f"{sentido} {qty_str} - {tipo} {s} a {e}"
    elif leg.price_type in (PriceType.FIX, PriceType.C2R) and leg.fixing_date:
        return f"{sentido} {qty_str} - {tipo} {leg.fixing_date.strftime('%d/%m/%Y')}"
    else:
        return f"{sentido} {qty_str} - {tipo}"


def build_pt_summary(
    trade: RfqTrade,
    company_header: Optional[str] = None,
) -> str:
    """Build a simplified one-line Portuguese summary.

    Example output: ``Alcast Brasil: Vende 3000T - Média Abril 2026``
    For swaps:      ``Alcast Brasil: Compra 3000T - Média Abril 2026 / Vende 3000T - Fix 30/04/2026``
    """
    header = company_header or "Alcast"
    parts = [_leg_summary_pt(trade.leg1)]
    if trade.trade_type == TradeType.SWAP and trade.leg2 is not None:
        parts.append(_leg_summary_pt(trade.leg2))
    return f"{header}: {' / '.join(parts)}"


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
