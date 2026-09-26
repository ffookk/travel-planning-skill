"""Explicit monetary scope for travel quotes; never convert or combine currencies."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any


BASIS_LABELS = {
    "per_person": "人", "per_adult": "成人", "group": "组",
    "per_vehicle": "车", "per_item": "项", "per_room_per_night": "间夜",
}
TAX_LABELS = {"included": "含税费", "excluded": "未含税费", "unknown": "税费待核"}


def amount(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Cost amount must be finite and nonnegative")
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("Cost amount must be finite and nonnegative") from None
    if not number.is_finite() or number < 0:
        raise ValueError("Cost amount must be finite and nonnegative")
    if number.is_zero():
        return Decimal(0)
    if number.adjusted() >= 1000 or number.as_tuple().exponent < -1000:
        raise ValueError("Cost amount exceeds the supported display precision")
    return number


def positive_count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 1000000:
        raise ValueError("Cost quantity must be a positive integer no greater than 1000000")
    return value


def number_text(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def structured(quote: Any) -> bool:
    if not isinstance(quote, dict):
        return False
    legacy = {"amount_yuan_for_4", "amount_yuan_per_person", "amount_yuan_per_adult"}
    return "amount" in quote or (not legacy.intersection(quote) and any(key in quote for key in ("currency", "basis")))


def validate_quote(quote: dict[str, Any]) -> tuple[Decimal, str, str]:
    value = amount(quote.get("amount"))
    currency = quote.get("currency")
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("Cost currency must be an explicit three-letter uppercase code")
    basis = quote.get("basis")
    if not isinstance(basis, str) or basis not in BASIS_LABELS:
        raise ValueError("Cost basis must describe an explicit supported pricing unit")
    if quote.get("traveler_count") is not None:
        positive_count(quote["traveler_count"])
    if quote.get("taxes") is not None and (not isinstance(quote["taxes"], str) or quote["taxes"] not in TAX_LABELS):
        raise ValueError("Cost taxes must be included, excluded, or unknown")
    return value, currency, basis


def quote_display(quote: dict[str, Any]) -> str:
    value, currency, basis = validate_quote(quote)
    supplied = quote.get("display")
    if isinstance(supplied, str) and supplied.strip():
        return supplied
    result = f"{currency} {number_text(value)}/{BASIS_LABELS[basis]}"
    if quote.get("traveler_count") is not None:
        result += f"（适用 {quote['traveler_count']} 人）"
    if quote.get("taxes") is not None:
        result += f" · {TAX_LABELS[quote['taxes']]}"
    return result


def estimated_subtotal(quote: dict[str, Any], quantity: Any) -> str:
    value, currency, _ = validate_quote(quote)
    count = positive_count(quantity)
    with localcontext() as context:
        context.prec = max(28, len(value.as_tuple().digits) + len(str(count)))
        total = value * count
    return f"{currency} {number_text(total)}（规划估算，非供应商总价）"


def trip_count(trip: dict[str, Any]) -> int | None:
    explicit = trip.get("traveler_count")
    if explicit is not None:
        return positive_count(explicit)
    # Only a whole, unambiguous legacy count is usable; do not add adults/children from prose.
    text = str(trip.get("travelers") or "").strip()
    match = re.fullmatch(r"([1-9][0-9]*)\s*(?:位成人|成人|人|adults?|travelers?|travellers?)", text, re.IGNORECASE)
    return positive_count(int(match[1])) if match else None


def quote_count(quote: Any) -> int | None:
    if not isinstance(quote, dict):
        return None
    explicit = quote.get("traveler_count")
    count = positive_count(explicit) if explicit is not None else None
    if quote.get("amount_yuan_for_4") is not None:
        if count is not None and count != 4:
            raise ValueError("Legacy four-person cost conflicts with its explicit traveler_count")
        return 4
    return count


def audit_costs(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    blocking: list[str] = []
    warnings: list[str] = []
    try:
        count = trip_count(data.get("trip") or {})
    except ValueError as error:
        return [str(error)], warnings
    planning = data.get("planning") or {}
    routes = {str(item.get("id")): item for field in ("transport_edges", "intercity_options") for item in planning.get(field) or []}

    def check(quote: Any, label: str) -> None:
        if not isinstance(quote, dict):
            return
        try:
            if structured(quote):
                validate_quote(quote)
            scope = quote_count(quote)
            if scope is not None and count is None:
                warnings.append(f"{label}: set trip.traveler_count to verify the quote's party size")
            elif scope is not None and scope != count:
                blocking.append(f"{label}: quote covers {scope} travelers but the trip has {count}")
        except ValueError as error:
            blocking.append(f"{label}: {error}")

    checked_routes: set[str] = set()
    for day in data.get("days") or []:
        for event in day.get("events") or []:
            if event.get("type") == "transport":
                route_id = str(event.get("route_id") or "")
                if route_id not in checked_routes:
                    route = routes.get(route_id) or {}
                    check(route.get("cost_quote", route.get("cost")), "Selected transport cost")
                    checked_routes.add(route_id)
            baseline_groups: set[str] = set()
            for item in event.get("cost_items") or []:
                quote = item.get("price_evidence", item.get("price", item.get("unit_price")))
                check(quote, "Event cost")
                if isinstance(quote, dict) and item.get("quantity") not in (None, "待核"):
                    try:
                        positive_count(item["quantity"])
                    except ValueError as error:
                        blocking.append(str(error))
                group = item.get("alternative_group")
                if group and item.get("pricing_role") == "baseline":
                    if not isinstance(group, str):
                        blocking.append("Cost alternative_group must be a string")
                    elif group in baseline_groups:
                        blocking.append("Alternative cost options cannot both be included in the same baseline group")
                    else:
                        baseline_groups.add(group)
    return list(dict.fromkeys(blocking)), list(dict.fromkeys(warnings))
