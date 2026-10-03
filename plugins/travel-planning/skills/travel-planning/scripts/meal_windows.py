"""Compare execution slots with researched meal windows without inventing hours."""

from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import Any


def check(slot: dict[str, Any], meal: dict[str, Any], day: dict[str, Any], trip: dict[str, Any],
          schedule: Any, parent: dict[str, Any] | None = None) -> tuple[bool, list[str], list[str]]:
    """Return outside-window status, timing errors, and unresolved constraints."""
    errors: list[str] = []
    pending: list[str] = []
    slot_day = dict(day)
    if parent is not None:
        slot_day["timezone"] = schedule.timezone_name(parent, day, trip)
        if schedule.dated(slot):
            slot_day["date"] = str(slot.get("start_at") or "")[:10]
    try:
        start, end = schedule.window(slot, slot_day, trip)
        if start is None or end is None:
            return False, ["Meal execution requires a start and end time"], []
        if schedule.instant(end) < schedule.instant(start):
            return False, ["Meal execution end precedes its start"], []
        location = schedule.zone(schedule.timezone_name(slot, slot_day, trip))
        if location is not None:
            start, end = start.astimezone(location), end.astimezone(location)
    except ValueError as error:
        return False, [str(error)], []

    if not meal:
        return False, [], []

    match = re.fullmatch(r"\s*([0-2]?\d:[0-5]\d)\s*[-–—]\s*([0-2]?\d:[0-5]\d)\s*", str(meal.get("time_window") or ""))
    opening, closing = (schedule.clock(match[1]), schedule.clock(match[2])) if match else (None, None)
    if opening is None or closing is None or closing < opening:
        return False, errors, ["Meal time_window needs manual recheck: expected one same-day HH:MM-HH:MM interval"]

    outside = False
    try:
        researched_date = date.fromisoformat(str(day.get("date")))
    except ValueError:
        researched_date = None
    if researched_date is not None and start.date() != researched_date:
        outside = True
    if location is None and start.utcoffset() != end.utcoffset():
        pending.append("Meal window needs an IANA timezone when execution endpoint offsets differ")
        minute = start.hour * 60 + start.minute + start.second / 60 + start.microsecond / 60_000_000
        return outside or minute < opening or minute > closing, errors, pending

    def boundary(minute: int) -> datetime:
        value = datetime.combine(start.date(), time(minute // 60, minute % 60))
        if location is not None:
            return schedule.localize(value, location)
        return value.replace(tzinfo=start.tzinfo)

    try:
        lower, upper = boundary(opening), boundary(closing)
    except ValueError:
        pending.append("Meal time_window crosses an ambiguous or nonexistent local boundary; research dated bounds before relying on it")
        return outside, errors, pending
    outside = outside or schedule.instant(start) < schedule.instant(lower) or schedule.instant(end) > schedule.instant(upper)
    return outside, errors, pending
