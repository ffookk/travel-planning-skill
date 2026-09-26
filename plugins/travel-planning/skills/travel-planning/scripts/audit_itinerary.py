#!/usr/bin/env python3
"""Audit a merged itinerary before rendering the final HTML artifact."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Any


RENDERER_PATH = Path(__file__).with_name("render_itinerary.py")
SPEC = importlib.util.spec_from_file_location("render_itinerary", RENDERER_PATH)
assert SPEC and SPEC.loader
render_itinerary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_itinerary)


COST_SPEC = importlib.util.spec_from_file_location("travel_cost_contract", Path(__file__).with_name("cost_contract.py"))
assert COST_SPEC and COST_SPEC.loader
cost_contract = importlib.util.module_from_spec(COST_SPEC)
COST_SPEC.loader.exec_module(cost_contract)

REPORT_PHRASES = ("综合考虑", "总体而言", "值得一去", "丰富体验", "感受当地", "合理安排", "行程亮点")
TRANSPORT_COVERAGE_SORTS = {2, 3, 4, 6, 7}
STRONG_AVAILABILITY_CLAIMS = {"available", "confirmed", "verified", "booked", "有房", "可订", "已确认"}


def minute_of(value: Any) -> int | None:
    text = str(value or "")
    parts = text.split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return None
    hour, minute = int(parts[0]), int(parts[1])
    if hour > 23 or minute > 59:
        return None
    return hour * 60 + minute


def minute_range(value: Any) -> tuple[int, int] | None:
    text = str(value or "").replace("—", "–").replace("-", "–")
    parts = [part.strip() for part in text.split("–")]
    if len(parts) != 2:
        return None
    start, end = minute_of(parts[0]), minute_of(parts[1])
    if start is None or end is None or end < start:
        return None
    return start, end


def event_text(event: dict[str, Any]) -> str:
    values: list[str] = []
    for field in ("title", "subtitle"):
        if event.get(field):
            values.append(str(event[field]))
    values.extend(str(value) for value in event.get("details") or [])
    values.extend(str(value) for value in event.get("tips") or [])
    return " ".join(values)


def transport_coverage_key(snapshot: dict[str, Any]) -> str | None:
    if snapshot.get("snapshot_kind") != "quote" or snapshot.get("product_type") not in {"flight", "train"}:
        return None
    query = snapshot.get("query") or {}
    if query.get("transport_no"):
        return None
    identifying = {
        key: query.get(key)
        for key in ("origin", "destination", "dep_date", "journey_type", "seat_class_name")
    }
    return json.dumps(identifying, ensure_ascii=False, sort_keys=True)


def audit(data: dict[str, Any]) -> dict[str, Any]:
    blocking: list[str] = []
    warnings: list[str] = []
    cost_blocking, cost_warnings = cost_contract.audit_costs(data)
    blocking.extend(cost_blocking)
    warnings.extend(cost_warnings)
    try:
        render_itinerary.validate_data(data)
    except ValueError as error:
        blocking.append(str(error))

    planning = data.get("planning") or {}
    meals = {item.get("id"): item for item in planning.get("meal_options") or []}
    source_snapshots = {
        str(item.get("snapshot_id")): item
        for item in planning.get("source_snapshots") or []
        if item.get("snapshot_id")
    }
    inventory_candidates = {
        str(item.get("id")): item
        for item in [
            *(planning.get("transport_edges") or []),
            *(planning.get("intercity_options") or []),
            *(planning.get("lodging_options") or []),
        ]
        if item.get("id")
    }
    selected_inventory_refs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    checked_event_ids: list[str] = []
    used_meal_ids: set[str] = set()

    for day in data.get("days") or []:
        events = day.get("events") or []
        day_name = day.get("date") or day.get("label") or "未命名日期"
        previous_end: int | None = None
        timed_events: list[tuple[int, int, dict[str, Any]]] = []
        for event in events:
            if event.get("id"):
                checked_event_ids.append(str(event["id"]))
            elif (data.get("workflow") or {}).get("phase") in {"confirmed_planning", "final"}:
                blocking.append(f"{day_name} 事件“{event.get('title') or '未命名'}”缺少稳定 id")
            if event.get("type") == "attraction":
                execution = event.get("execution") or {}
                checkpoints = execution.get("checkpoints") or []
                if not checkpoints:
                    blocking.append(f"{day_name} 景点“{event.get('title') or '未命名'}”缺少必达卡点和内部顺序")
                orders = [point.get("order") for point in checkpoints]
                if checkpoints and orders != list(range(1, len(checkpoints) + 1)):
                    blocking.append(f"{day_name} 景点“{event.get('title') or '未命名'}”的 checkpoint order 必须从1连续递增")
                checkpoint_previous_end: int | None = None
                event_start = minute_of(event.get("time"))
                event_end = minute_of(event.get("end_time"))
                for point in checkpoints:
                    point_start = minute_of(point.get("time"))
                    point_end = minute_of(point.get("end_time"))
                    point_name = point.get("name") or point.get("id") or "未命名节点"
                    if point_start is None or point_end is None:
                        blocking.append(f"{day_name} 景点节点“{point_name}”必须提供 HH:MM 的 time 和 end_time")
                        continue
                    if point_end < point_start:
                        blocking.append(f"{day_name} 景点节点“{point_name}”的 end_time 早于 time")
                    if checkpoint_previous_end is not None and point_start < checkpoint_previous_end:
                        blocking.append(f"{day_name} 景点节点“{point_name}”与前一节点时间重叠")
                    if event_start is not None and point_start < event_start:
                        blocking.append(f"{day_name} 景点节点“{point_name}”早于外层景点事件")
                    if event_end is not None and point_end > event_end:
                        blocking.append(f"{day_name} 景点节点“{point_name}”晚于外层景点事件")
                    checkpoint_previous_end = point_end
                    for image in point.get("images") or []:
                        required_image = {"url", "alt", "source_url", "license"}
                        missing_image = sorted(field for field in required_image if not image.get(field))
                        if missing_image or not (image.get("author") or image.get("source_label")):
                            blocking.append(f"{day_name} 景点节点“{point_name}”的图片缺少 alt、作者/机构、许可或原始页面")
                    if point.get("meal_id"):
                        used_meal_ids.add(str(point["meal_id"]))
            start = minute_of(event.get("time"))
            end = minute_of(event.get("end_time"))
            if start is None:
                blocking.append(f"{day_name} 事件“{event.get('title') or '未命名'}”的 time 必须是 HH:MM")
                continue
            if previous_end is not None and start < previous_end:
                blocking.append(f"{day_name} 事件“{event.get('title') or '未命名'}”与前一事件时间重叠或顺序倒置")
            if end is not None and end < start:
                blocking.append(f"{day_name} 事件“{event.get('title') or '未命名'}”的 end_time 早于 time")
            timed_events.append((start, end if end is not None else start, event))
            previous_end = end if end is not None else start

            if event.get("type") == "meal" and event.get("meal_id"):
                meal_id = str(event["meal_id"])
                used_meal_ids.add(meal_id)
                meal = meals.get(meal_id) or {}
                allowed = minute_range(meal.get("time_window"))
                if end is None:
                    blocking.append(f"{day_name} 餐饮事件“{event.get('title') or meal_id}”必须提供 end_time")
                elif allowed and (start < allowed[0] or end > allowed[1]):
                    blocking.append(
                        f"{day_name} 餐饮事件“{event.get('title') or meal_id}”的事件时间超出 meal_option.time_window"
                    )

            candidate_id = event.get("route_id") if event.get("type") == "transport" else event.get("lodging_id") if event.get("type") == "lodging" else None
            candidate = inventory_candidates.get(str(candidate_id or "")) or {}
            for ref in candidate.get("inventory_refs") or []:
                selected_inventory_refs.append((candidate, ref))

            text = event_text(event)
            found = [phrase for phrase in REPORT_PHRASES if phrase in text]
            if found:
                warnings.append(f"{day_name} 事件“{event.get('title') or '未命名'}”含汇报式措辞：{'、'.join(found)}")

        if not timed_events:
            continue
        day_start = min(start for start, _, _ in timed_events)
        day_end = max(end for _, end, _ in timed_events)
        exemptions = day.get("meal_exemptions") or {}
        for meal_type, center in (("午餐", 12 * 60 + 30), ("晚餐", 19 * 60)):
            if not (day_start <= center <= day_end) or exemptions.get(meal_type):
                continue
            has_meal = any(
                event.get("type") == "meal" and (meals.get(event.get("meal_id")) or {}).get("meal_type") == meal_type
                for _, _, event in timed_events
            )
            if not has_meal:
                blocking.append(f"{day_name} 跨过{meal_type}窗口但没有绑定 meal_id 的{meal_type}事件")

    blocking = list(dict.fromkeys(blocking))
    unused_meals = sorted(str(meal_id) for meal_id in meals if meal_id not in used_meal_ids)
    if unused_meals:
        warnings.append(f"存在未绑定到事件或景点节点的 meal_options：{'、'.join(unused_meals)}")
    warnings = list(dict.fromkeys(warnings))
    now_value = datetime.now().astimezone()
    expired_snapshot_ids: set[str] = set()
    checked_inventory_refs: set[tuple[str, str]] = set()
    coverage_by_query: dict[str, set[int]] = {}
    for snapshot in source_snapshots.values():
        key = transport_coverage_key(snapshot)
        sort_type = (snapshot.get("query") or {}).get("sort_type")
        if key and isinstance(sort_type, int):
            coverage_by_query.setdefault(key, set()).add(sort_type)
    selected_coverage_keys: set[str] = set()
    coverage_gaps: list[str] = []
    lodging_verification_issues: list[str] = []
    for candidate, ref in selected_inventory_refs:
        snapshot_id = str(ref.get("snapshot_id") or "")
        offer_id = str(ref.get("offer_id") or "")
        if (snapshot_id, offer_id) in checked_inventory_refs:
            continue
        checked_inventory_refs.add((snapshot_id, offer_id))
        snapshot = source_snapshots.get(snapshot_id) or {}
        item = next(
            (entry for entry in snapshot.get("items") or [] if str(entry.get("offer_id") or "") == offer_id),
            {},
        )
        coverage_key = transport_coverage_key(snapshot)
        if coverage_key:
            selected_coverage_keys.add(coverage_key)
        if snapshot.get("product_type") == "hotel":
            requested = (snapshot.get("query") or {}).get("requested_occupancy") or {}
            requirement = candidate.get("room_requirement") or {}
            requested_rooms = requested.get("rooms")
            requested_adults = requested.get("adults")
            if not requested_rooms or not requested_adults:
                lodging_verification_issues.append(
                    f"住宿候选“{candidate.get('id') or '未命名'}”的报价快照没有记录成人数和房间数"
                )
            elif requirement and (
                requested_rooms != requirement.get("rooms")
                or requested_adults != requirement.get("travelers")
            ):
                lodging_verification_issues.append(
                    f"住宿候选“{candidate.get('id') or '未命名'}”的报价人数/房间数与行程需求不一致"
                )
            availability = item.get("availability") or {}
            selection_status = str(candidate.get("selection_status") or "").casefold()
            if availability.get("remaining") is None and selection_status in STRONG_AVAILABILITY_CLAIMS:
                blocking.append(
                    f"住宿候选“{candidate.get('id') or '未命名'}”没有多间同房型库存证据，不能标记为有房或已确认"
                )
            location_verification = candidate.get("location_verification") or {}
            if location_verification.get("status") != "verified":
                lodging_verification_issues.append(
                    f"住宿候选“{candidate.get('id') or '未命名'}”尚未完成酒店全名、城市/行政区、地址和坐标核验"
                )
        expires_at = (snapshot.get("freshness") or {}).get("expires_at")
        if expires_at:
            try:
                expires = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                if expires < now_value:
                    expired_snapshot_ids.add(snapshot_id)
            except ValueError:
                pass
        if snapshot.get("product_type") == "train" and (
            candidate.get("country_code") == "CN"
            or (candidate.get("rail_verification") or {}).get("channel") == "12306"
        ):
            verification = candidate.get("rail_verification") or {}
            if not verification.get("action_link") or verification.get("channel") != "12306":
                blocking.append(f"铁路候选“{candidate.get('id') or '未命名'}”缺少 12306 最终复核入口")
            elif (data.get("workflow") or {}).get("phase") == "final" and verification.get("status") != "verified":
                blocking.append(f"最终铁路候选“{candidate.get('id') or '未命名'}”尚未完成 12306 复核")
    for key in sorted(selected_coverage_keys):
        missing = sorted(TRANSPORT_COVERAGE_SORTS - coverage_by_query.get(key, set()))
        if missing:
            coverage_gaps.append(f"所选开放式交通查询缺少排序覆盖：{','.join(str(value) for value in missing)}")
    phase = (data.get("workflow") or {}).get("phase")
    for message in coverage_gaps + lodging_verification_issues:
        if phase == "final":
            blocking.append(message)
        else:
            warnings.append(message)
    if expired_snapshot_ids:
        message = f"已选酒旅报价或运行快照已过期：{'、'.join(sorted(expired_snapshot_ids))}"
        if (data.get("workflow") or {}).get("phase") == "final":
            blocking.append(message)
        else:
            warnings.append(message)
    blocking = list(dict.fromkeys(blocking))
    warnings = list(dict.fromkeys(warnings))
    return {
        "status": "pass" if not blocking else "fail",
        "blocking": blocking,
        "warnings": warnings,
        "restaurant_audit": {
            "meal_slot_count": len(meals),
            "used_meal_slot_count": len(used_meal_ids),
            "candidate_reference_count": sum(len(meal.get("candidate_ids") or []) for meal in meals.values()),
            "restaurant_count": len(planning.get("restaurants") or []),
            "snapshot_count": len(planning.get("restaurant_snapshots") or []),
            "baseline_route_count": len(planning.get("meal_baseline_routes") or []),
            "route_evaluation_count": len(planning.get("meal_route_evaluations") or []),
            "community_reference_count": sum(
                len((snapshot.get("community_consensus") or {}).get("references") or [])
                for snapshot in planning.get("restaurant_snapshots") or []
            ),
            "source_registry_count": len(data.get("sources") or []),
        },
        "inventory_audit": {
            "snapshot_count": len(source_snapshots),
            "selected_reference_count": len(checked_inventory_refs),
            "expired_snapshot_ids": sorted(expired_snapshot_ids),
            "transport_coverage_gaps": coverage_gaps,
            "lodging_verification_issues": lodging_verification_issues,
        },
        "checked_event_ids": checked_event_ids,
        "checked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = audit(data)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    raise SystemExit(0 if result["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
