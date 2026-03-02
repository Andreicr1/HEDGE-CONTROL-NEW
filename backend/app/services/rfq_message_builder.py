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
    qty = int(leg.quantity_mt) if float(int(leg.quantity_mt)) == float(leg.quantity_mt) else leg.quantity_mt

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
