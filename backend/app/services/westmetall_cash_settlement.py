from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import re

import httpx


WESTMETALL_DAILY_URL = "https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Al_cash"

SYMBOL_DAILY = "LME_ALU_CASH_SETTLEMENT_DAILY"
SOURCE_WESTMETALL = "westmetall"


class WestmetallLayoutError(RuntimeError):
    pass


@dataclass(frozen=True)
class WestmetallFetchEvidence:
    source_url: str
    html_sha256: str
    fetched_at: datetime


@dataclass(frozen=True)
class WestmetallDailyRow:
    settlement_date: date
    price_usd: float


def fetch_westmetall_html(url: str, *, timeout_seconds: float = 30.0) -> tuple[bytes, WestmetallFetchEvidence]:
    fetched_at = datetime.now(timezone.utc)
    response = httpx.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    html = response.content
    html_sha256 = hashlib.sha256(html).hexdigest()
    evidence = WestmetallFetchEvidence(source_url=url, html_sha256=html_sha256, fetched_at=fetched_at)
    return html, evidence


_DATE_RE = re.compile(r"^(?P<d>\d{2})\.(?P<m>\d{2})\.(?P<y>\d{4})$")


def _parse_dd_mm_yyyy(value: str) -> date | None:
    m = _DATE_RE.match(value.strip())
    if not m:
        return None
    return date(int(m.group("y")), int(m.group("m")), int(m.group("d")))


def _parse_float(value: str) -> float | None:
    cleaned = value.strip().replace("\xa0", " ").replace(" ", "")
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


_TD_RE = re.compile(r"<t[dh][^>]*>(?P<content>.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def parse_westmetall_daily_rows(html: bytes) -> list[WestmetallDailyRow]:
    text = html.decode("utf-8", errors="replace")

    rows: list[WestmetallDailyRow] = []
    for tr in re.findall(r"<tr[^>]*>.*?</tr>", text, flags=re.IGNORECASE | re.DOTALL):
        cells = []
        for cell in _TD_RE.findall(tr):
            cell_text = _TAG_RE.sub("", cell)
            cell_text = cell_text.strip()
            if cell_text:
                cells.append(cell_text)
        if len(cells) < 2:
            continue
        parsed_date = _parse_dd_mm_yyyy(cells[0])
        if not parsed_date:
            continue
        parsed_price = _parse_float(cells[1])
        if parsed_price is None:
            continue
        rows.append(WestmetallDailyRow(settlement_date=parsed_date, price_usd=parsed_price))

    if not rows:
        raise WestmetallLayoutError("no_daily_rows_parsed")
    return rows

