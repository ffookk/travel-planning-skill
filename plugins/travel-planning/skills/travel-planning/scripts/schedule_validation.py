"""Optional dated event times and conservative itinerary feasibility checks."""

from __future__ import annotations

import math
import re
from datetime import date, datetime, time, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})\Z")
CLOCK = re.compile(r"([01]?\d|2[0-3]):([0-5]\d)\Z")


def clock(value: Any) -> int | None:
    match = CLOCK.fullmatch(str(value or "").strip())
    return int(match[1]) * 60 + int(match[2]) if match else None


def zone(name: Any) -> ZoneInfo | None:
    if name is None:
        return None
    if not isinstance(name, str) or not name:
        raise ValueError("timezone must be an IANA timezone name")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(f"Unknown IANA timezone: {name}") from None


def timestamp(value: Any, name: Any = None) -> datetime:
    if not isinstance(value, str) or not STAMP.fullmatch(value):
        raise ValueError("dated times must be ISO date-times with an explicit UTC offset")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("invalid dated time") from None
    location = zone(name)
    if location is not None:
        local = result.astimezone(location)
        if local.replace(tzinfo=None) != result.replace(tzinfo=None) or local.utcoffset() != result.utcoffset():
            raise ValueError("dated time offset or local time does not match its IANA timezone")
    return result


def localize(value: datetime, location: ZoneInfo) -> datetime:
    """Require an explicit offset when the local clock is absent or repeated."""
    candidates = {}
    for fold in (0, 1):
        candidate = value.replace(tzinfo=location, fold=fold)
        instant = candidate.astimezone(timezone.utc)
        if instant.astimezone(location).replace(tzinfo=None) == value:
            candidates[instant] = candidate
    if len(candidates) != 1:
        state = "ambiguous" if candidates else "nonexistent"
        raise ValueError(f"{state} local time; provide start_at/end_at with valid explicit offsets")
    return next(iter(candidates.values()))


def instant(value: datetime) -> datetime:
    return value.astimezone(timezone.utc) if value.utcoffset() is not None else value


def dated(item: dict[str, Any]) -> bool:
    return "start_at" in item or "end_at" in item


def timezone_name(item: dict[str, Any], day: dict[str, Any], trip: dict[str, Any]) -> Any:
    return item.get("timezone", day.get("timezone", trip.get("timezone")))


def window(item: dict[str, Any], day: dict[str, Any], trip: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    name = timezone_name(item, day, trip)
    location = zone(name)
    if dated(item):
        if "start_at" not in item or "end_at" not in item:
            raise ValueError("start_at and end_at must be supplied together")
        start = timestamp(item["start_at"], name)
        end = timestamp(item["end_at"], item.get("end_timezone", name))
        if instant(end) < instant(start):
            raise ValueError("end_at precedes start_at as an actual instant")
        if day.get("date") and str(day["date"]) != start.date().isoformat():
            raise ValueError("day.date must match the local departure date in start_at")
        for field, value in (("time", start), ("end_time", end)):
            if item.get(field) is not None and clock(item[field]) != value.hour * 60 + value.minute:
                raise ValueError(f"{field} must match the local clock in the dated time")
        return start, end
    if "end_timezone" in item:
        raise ValueError("end_timezone requires start_at and end_at")
    start_minute, end_minute = clock(item.get("time")), clock(item.get("end_time"))
    if start_minute is None:
        if location is not None:
            raise ValueError("timezone-aware events require HH:MM or start_at/end_at")
        return None, None
    try:
        day_date = date.fromisoformat(str(day.get("date"))) if day.get("date") else date(2000, 1, 1)
    except ValueError:
        if location is not None:
            raise ValueError("timezone-aware events require a valid day.date") from None
        day_date = date(2000, 1, 1)
    if location is not None and not day.get("date"):
        raise ValueError("timezone-aware events require day.date")
    def at(minute: int | None) -> datetime | None:
        if minute is None:
            return None
        result = datetime.combine(day_date, time(minute // 60, minute % 60))
        return localize(result, location) if location is not None else result
    start, end = at(start_minute), at(end_minute)
    if location is not None and end is not None and instant(end) < instant(start):
        raise ValueError("overnight events require explicit start_at/end_at dates")
    return start, end


def temporal_fields(data: dict[str, Any]) -> None:
    """Validate only opt-in fields so ordinary renderer behavior stays compatible."""
    trip = data.get("trip") or {}
    zone(trip.get("timezone"))
    for day in data.get("days") or []:
        zone(day.get("timezone"))
        for event in day.get("events") or []:
            opted_in = dated(event) or timezone_name(event, day, trip) is not None or "end_timezone" in event
            if opted_in:
                window(event, day, trip)
            for point in (event.get("execution") or {}).get("checkpoints") or []:
                if dated(point) or point.get("timezone") is not None or "end_timezone" in point:
                    if not opted_in:
                        raise ValueError("dated checkpoints require a dated or timezone-aware parent event")
                    point_day = {"date": str(point.get("start_at") or "")[:10] or day.get("date"), "timezone": timezone_name(event, day, trip)}
                    window(point, point_day, trip)


def display_time(item: dict[str, Any], end: bool = False) -> str:
    value = item.get("end_at" if end else "start_at")
    return str(value).replace("T", " ") if value else str(item.get("end_time" if end else "time") or "")


def numeric_minutes(route: dict[str, Any]) -> tuple[float | None, bool]:
    if "door_to_door_minutes" in route:
        value = route["door_to_door_minutes"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("door_to_door_minutes must be a finite nonnegative number")
        try:
            minutes = float(value)
        except (OverflowError, ValueError):
            raise ValueError("door_to_door_minutes must be a finite nonnegative number") from None
        if not math.isfinite(minutes) or minutes < 0:
            raise ValueError("door_to_door_minutes must be a finite nonnegative number")
        return minutes, True
    text = str(route.get("door_to_door_duration") or "").strip()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:分钟|minutes?|mins?)", text, re.IGNORECASE)
    if not match:
        return None, bool(text)
    minutes = float(match[1])
    if not math.isfinite(minutes):
        raise ValueError("door_to_door_duration must contain a finite minute value")
    return minutes, True


def feasibility(event: dict[str, Any], candidate: dict[str, Any], start: datetime | None, end: datetime | None,
                *, event_timezone: Any = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    pending: list[str] = []
    if event.get("type") == "transport":
        minutes, supplied = numeric_minutes(candidate)
        if minutes is None and supplied:
            pending.append("Transport duration needs manual recheck: door_to_door_duration is not an exact minute value")
        elif minutes is not None:
            if start is None or end is None:
                pending.append("Transport duration needs an event end time before feasibility can be checked")
            elif (instant(end) - instant(start)).total_seconds() / 60 < minutes:
                errors.append("Allocated transport time is shorter than door_to_door_minutes")
    if event.get("type") != "attraction" or start is None:
        return errors, pending
    admission = event.get("admission") or {}
    admission_zone = zone(admission.get("timezone", event.get("timezone", event_timezone)))
    if admission_zone is None and isinstance(start.tzinfo, ZoneInfo):
        admission_zone = start.tzinfo
    if admission_zone is not None:
        if start.utcoffset() is None:
            pending.append("Admission timezone needs an event timezone or start_at before comparison")
            return errors, pending
        start = start.astimezone(admission_zone)
        end = end.astimezone(admission_zone) if end is not None else None
    unresolved_local_end = admission_zone is None and end is not None and start.utcoffset() != end.utcoffset()
    local_minute = start.hour * 60 + start.minute + start.second / 60 + start.microsecond / 60_000_000
    if admission.get("last_entry_at") is not None:
        cutoff = timestamp(admission["last_entry_at"], admission.get("timezone"))
        if start.utcoffset() is None:
            pending.append("Last entry instant needs an event timezone or start_at before comparison")
        elif instant(start) > instant(cutoff):
            errors.append("Arrival is after last_entry_at")
    elif admission.get("last_entry"):
        cutoff = clock(admission["last_entry"])
        if cutoff is None:
            pending.append("Last entry needs manual recheck: last_entry is not an exact HH:MM time")
        elif local_minute > cutoff:
            errors.append("Arrival is after last_entry")
    windows = admission.get("opening_windows")
    if windows is not None:
        if not isinstance(windows, list) or not windows:
            raise ValueError("opening_windows must be a nonempty list of dated start_at/end_at windows")
        parsed = []
        for item in windows:
            if not isinstance(item, dict):
                raise ValueError("opening_windows entries must be objects")
            opening = timestamp(item.get("start_at"), admission.get("timezone"))
            closing = timestamp(item.get("end_at"), admission.get("timezone"))
            if instant(closing) <= instant(opening):
                raise ValueError("opening window end_at must be later than start_at")
            parsed.append((instant(opening), instant(closing)))
        if start.utcoffset() is None:
            pending.append("Opening windows need an event timezone or start_at before comparison")
        elif not any(a <= instant(start) < b and (end is None or instant(end) <= b) for a, b in parsed):
            errors.append("Attraction visit is outside opening_windows")
    elif admission.get("opening_hours"):
        match = re.fullmatch(r"\s*([0-2]?\d:[0-5]\d)\s*[-–—]\s*([0-2]?\d:[0-5]\d)\s*", str(admission["opening_hours"]))
        opening, closing = (clock(match[1]), clock(match[2])) if match else (None, None)
        if opening is None or closing is None or closing <= opening:
            pending.append("Opening hours need manual recheck or dated opening_windows")
        elif unresolved_local_end:
            pending.append("Opening hours need an IANA venue timezone or dated opening_windows when endpoint offsets differ")
            if local_minute < opening or local_minute >= closing:
                errors.append("Attraction arrival is outside opening_hours")
        elif local_minute < opening or local_minute >= closing or (end is not None and (end.date() != start.date() or end.hour * 60 + end.minute + end.second / 60 + end.microsecond / 60_000_000 > closing)):
            errors.append("Attraction visit is outside opening_hours")
    return errors, pending


def audit_schedule(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    pending: list[str] = []
    trip = data.get("trip") or {}
    planning = data.get("planning") or {}
    routes = {str(item.get("id")): item for item in [*(planning.get("transport_edges") or []), *(planning.get("intercity_options") or [])]}
    previous_instant: datetime | None = None
    previous_was_aware: bool | None = None
    for day in data.get("days") or []:
        for event in day.get("events") or []:
            label = str(event.get("id") or event.get("title") or "event")
            try:
                start, end = window(event, day, trip)
                aware = start is not None and start.utcoffset() is not None
                if aware:
                    if previous_instant is not None and instant(start) < previous_instant:
                        errors.append(f"{label}: actual event times overlap or are out of order")
                    previous_instant = instant(end or start)
                if previous_was_aware is not None and previous_was_aware != aware:
                    pending.append(f"{label}: mixed dated and timezone-free events need a timezone to verify their boundary")
                previous_was_aware = aware
                failures, warnings = feasibility(
                    event, routes.get(str(event.get("route_id")), {}), start, end,
                    event_timezone=timezone_name(event, day, trip),
                )
                errors.extend(f"{label}: {message}" for message in failures)
                pending.extend(f"{label}: {message}" for message in warnings)
                if aware and end is not None and (start.date() != end.date() or start.utcoffset() != end.utcoffset()):
                    pending.append(f"{label}: meal coverage during overnight or timezone-changing travel needs manual recheck")
                if aware or dated(event):
                    previous_point: datetime | None = None
                    for point in (event.get("execution") or {}).get("checkpoints") or []:
                        if end is not None and (start.date() != end.date() or start.utcoffset() != end.utcoffset()) and not dated(point):
                            raise ValueError("overnight or offset-changing attraction checkpoints require explicit start_at/end_at")
                        point_day = {"date": str(point.get("start_at") or "")[:10] or day.get("date"), "timezone": timezone_name(event, day, trip)}
                        point_start, point_end = window(point, point_day, trip)
                        if point_start is None or point_end is None:
                            raise ValueError("checkpoint times are required")
                        if point_start.utcoffset() is None:
                            point_start = point_start.replace(tzinfo=start.tzinfo)
                            point_end = point_end.replace(tzinfo=start.tzinfo)
                        if instant(point_end) < instant(point_start) or (previous_point is not None and instant(point_start) < previous_point):
                            raise ValueError("checkpoint actual times overlap or are out of order")
                        if instant(point_start) < instant(start) or (end is not None and instant(point_end) > instant(end)):
                            raise ValueError("checkpoint actual times fall outside the attraction event")
                        previous_point = instant(point_end)
            except ValueError as error:
                errors.append(f"{label}: {error}")
    return errors, pending
