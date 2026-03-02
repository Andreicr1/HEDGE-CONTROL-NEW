"""LME (London Metal Exchange) business-day calendar.

Provides holiday-aware date arithmetic required by the RFQ engine for
computing PPT (Prompt Payment Terms) settlement dates.

The holiday set is pluggable.  A built-in constant ``LME_HOLIDAYS`` covers
official LME non-trading days from 2025 through 2035.  Load additional
holidays via ``add_holidays()`` or pass them at construction time.

Usage:
    from app.services.lme_calendar import lme_calendar, add_business_days

    cal = lme_calendar()                      # singleton w/ built-in holidays
    ppt = add_business_days(some_date, 2, cal) # 2 biz days after some_date
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Optional, Set


# ---------------------------------------------------------------------------
# Built-in LME holiday set (ISO YYYY-MM-DD)
#
# Source: LME Trading Calendar 2025–2035 (official publication).
# The user will supply the full data extracted from the PDF in a future phase.
# For now the set includes only 2025 and 2026 holidays that are publicly known.
# ---------------------------------------------------------------------------

LME_HOLIDAYS: set[str] = {
    # --- 2025 ---
    "2025-01-01",  # New Year's Day
    "2025-04-18",  # Good Friday
    "2025-04-21",  # Easter Monday
    "2025-05-05",  # Early May Bank Holiday
    "2025-05-26",  # Spring Bank Holiday
    "2025-08-25",  # Summer Bank Holiday
    "2025-12-25",  # Christmas Day
    "2025-12-26",  # Boxing Day
    # --- 2026 ---
    "2026-01-01",  # New Year's Day
    "2026-04-03",  # Good Friday
    "2026-04-06",  # Easter Monday
    "2026-05-04",  # Early May Bank Holiday
    "2026-05-25",  # Spring Bank Holiday
    "2026-08-31",  # Summer Bank Holiday
    "2026-12-25",  # Christmas Day
    "2026-12-28",  # Boxing Day (substitute — 26 Dec is Saturday)
}


# ---------------------------------------------------------------------------
# Calendar class
# ---------------------------------------------------------------------------

class LMECalendar:
    """Holiday-aware business-day calendar.

    Default configuration: weekends (Sat/Sun) + the official LME non-trading
    days listed in ``LME_HOLIDAYS``.
    """

    def __init__(self, holidays_iso: Optional[Iterable[str]] = None) -> None:
        self._holidays: Set[str] = set(holidays_iso) if holidays_iso is not None else set()

    # -- queries --

    def is_business_day(self, d: date) -> bool:
        """Return True if *d* is a working day on the LME."""
        if d.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        return d.isoformat() not in self._holidays

    # -- mutations --

    def add_holidays(self, holidays_iso: Iterable[str]) -> None:
        """Merge additional ISO-date strings into the holiday set."""
        self._holidays.update(holidays_iso)


# ---------------------------------------------------------------------------
# Module-level date-arithmetic helpers
# ---------------------------------------------------------------------------

def add_business_days(start: date, n: int, cal: LMECalendar) -> date:
    """Return the date that is *n* business days after *start*.

    Counts forward day-by-day, skipping non-business days (weekends +
    holidays).  ``start`` itself is **not** counted.
    """
    d = start
    counted = 0
    while counted < n:
        d += timedelta(days=1)
        if cal.is_business_day(d):
            counted += 1
    return d


def second_business_day_of_next_month(
    year: int,
    month_index_0: int,
    cal: LMECalendar,
) -> date:
    """2nd business day of the month **following** the indicated month.

    Parameters
    ----------
    year:
        Calendar year.
    month_index_0:
        Zero-based month index (0 = January … 11 = December).
    """
    if month_index_0 == 11:
        y2, m2 = year + 1, 1
    else:
        y2, m2 = year, month_index_0 + 2  # datetime.date month is 1-based

    d = date(y2, m2, 1)
    count = 0
    while True:
        if cal.is_business_day(d):
            count += 1
            if count == 2:
                return d
        d += timedelta(days=1)


def last_business_day_of_month(
    year: int,
    month_index_0: int,
    cal: LMECalendar,
) -> date:
    """Last business day of the indicated month.

    Useful for auto-filling fixing dates when Fix is paired with AVG.
    """
    if month_index_0 == 11:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month_index_0 + 2, 1) - timedelta(days=1)
    while not cal.is_business_day(d):
        d -= timedelta(days=1)
    return d


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_SINGLETON: Optional[LMECalendar] = None


def lme_calendar() -> LMECalendar:
    """Return the module-level LME calendar singleton.

    Lazily initialised with the built-in ``LME_HOLIDAYS`` set.
    """
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = LMECalendar(LME_HOLIDAYS)
    return _SINGLETON


def reset_calendar() -> None:
    """Force-reset the singleton (useful for testing)."""
    global _SINGLETON
    _SINGLETON = None
