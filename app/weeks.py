

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TORONTO = ZoneInfo("America/Toronto")


def today() -> date:

    return datetime.now(TORONTO).date()


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def current_week() -> date:

    return monday_of(today())


def status_of(week_start: date) -> str:

    now = current_week()
    if week_start > now:
        return "scheduled"
    return "current" if week_start == now else "past"
