#!/usr/bin/env python3
"""Assemble the audited Qinghai-Gansu 2026 National Day research into one itinerary."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / ".travel-research" / "qinggan-loop-2026-10-01-beijing"
RESULTS = WORKSPACE / "results"
ARTIFACTS = WORKSPACE / "artifacts"


def load(name: str) -> dict[str, Any]:
    return json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))


def load_source_snapshots(*results: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for result in results:
        task_id = str(result.get("task_id") or "")
        for snapshot_id in result.get("source_snapshot_ids") or []:
            path = WORKSPACE / "snapshots" / task_id / f"{snapshot_id}.json"
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            existing = snapshots.get(str(snapshot_id))
            if existing is not None and existing != snapshot:
                raise ValueError(f"酒旅快照 ID 冲突：{snapshot_id}")
            snapshots[str(snapshot_id)] = snapshot
    return list(snapshots.values())


def by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in items}


def action(label: str, url: str, kind: str, provider: str, disclaimer: str) -> dict[str, str]:
    return {
        "type": kind,
        "label": label,
        "provider": provider,
        "url": url,
        "checked_at": "2026-09-21",
        "disclaimer": disclaimer,
    }


def normalize_actions(items: list[dict[str, Any]], kind: str, provider: str, disclaimer: str) -> list[dict[str, Any]]:
    result = []
    for item in items or []:
        if not str(item.get("url") or "").startswith("https://"):
            continue
        result.append({
            **item,
            "type": item.get("type") or kind,
            "provider": item.get("provider") or provider,
            "checked_at": item.get("checked_at") or "2026-09-21",
            "disclaimer": item.get("disclaimer") or disclaimer,
        })
    return result


def hm_to_minutes(value: str) -> int:
    hour, minute = (int(part) for part in value.split(":"))
    return hour * 60 + minute


def minutes_to_hm(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def add_minutes(value: str, delta: int) -> str:
    return minutes_to_hm(hm_to_minutes(value) + delta)


def format_money(value: Any) -> str:
    return "待官方核验" if value is None else f"¥{value}"


def normalize_cost(item: dict[str, Any]) -> dict[str, Any]:
    role = str(item.get("pricing_role") or "optional")
    if role in {"baseline", "baseline_if_required"}:
        pricing_role, required = "baseline", True
    elif role == "baseline_recommended":
        pricing_role, required = "optional", False
    elif role in {"fallback_alternative", "optional_alternative"}:
        pricing_role, required = "alternative", False
    else:
        pricing_role, required = "optional", False
    if role == "vehicle_cost":
        kind = "vehicle_cost"
    elif item.get("id", "").endswith("base") or role == "baseline":
        kind = "base_ticket"
    elif role in {"baseline_recommended", "baseline_if_required"}:
        kind = "internal_transport"
    else:
        kind = "optional_experience"
    return {
        "name": item.get("name"),
        "kind": kind,
        "unit_price": format_money(item.get("unit_price_cny")),
        "quantity": f"{item.get('quantity', 2)}人" if item.get("quantity") != 1 else "1车",
        "subtotal": format_money(item.get("subtotal_cny")),
        "pricing_role": pricing_role,
        "required": required,
        "status": item.get("status") or "to_recheck",
        "source_ids": item.get("source_ids") or [],
    }


def route_cost(value: Any) -> str:
    if not isinstance(value, dict):
        return str(value or "待实时查询")
    toll = value.get("tolls_yuan_platform")
    fare = value.get("fare") or "待实时查询"
    return f"{fare}" + (f"；平台估算路桥费约¥{toll}" if toll is not None else "")


def normalize_route(item: dict[str, Any]) -> dict[str, Any]:
    route = deepcopy(item)
    route["cost"] = route_cost(route.get("cost"))
    route["reason"] = route.get("reason") or route.get("recommendation_reason") or "承接当天相邻事件，减少折返"
    route["action_links"] = normalize_actions(
        route.get("action_links") or [], "map", "高德地图", "国庆路况会变化，出发时按实时导航复核"
    )
    map_route = route.get("map_route") or {}
    if map_route:
        map_route["assumption"] = map_route.get("assumption") or "坐标来自高德查询；最终酒店和上下车点确定后重算"
        route["map_route"] = map_route
    return route


def normalize_meal(item: dict[str, Any]) -> dict[str, Any]:
    meal_type = {
        "breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐",
        "breakfast_or_lunch": "早餐",
    }.get(str(item.get("meal")), str(item.get("meal") or "用餐"))
    return {
        **item,
        "meal_type": meal_type,
        "name": item.get("name") or item.get("area") or f"{meal_type}候选",
        "location": item.get("area") or "当天顺路片区",
        "signature_dishes": item.get("recommended_dishes") or [],
        "per_person": f"约¥{item.get('planning_cost_per_person_cny')}/人（规划带）",
        "opening_hours": "营业状态待出发前复核" if str(item.get("operating_status", "")).startswith("to_recheck") else item.get("operating_status"),
        "queue_note": item.get("queue_rule"),
        "why_here": item.get("route_fit"),
        "fallback": item.get("backup") or "排队或停业时改同路段即时有座的正规餐饮点",
        "action_links": normalize_actions(
            item.get("action_links") or [], "restaurant", "高德地图", "店铺营业、排队和菜单价格以到店前查询为准"
        ),
    }


def normalize_lodging(item: dict[str, Any]) -> dict[str, Any]:
    primary = item.get("primary") or {}
    backup = item.get("backup") or {}
    links = []
    for candidate, label in ((primary, "查看主选"), (backup, "查看备选")):
        links.extend(normalize_actions(candidate.get("action_links") or [], "hotel", "携程", "房态和含税总价以查询时为准"))
    return {
        **item,
        "name": primary.get("name") or f"{item.get('city')}住宿候选",
        "area": item.get("area_anchor"),
        "check_in": (item.get("nights") or [None])[0],
        "check_out": None,
        "price": "未取得本次日期实时含税价",
        "luggage_storage": item.get("luggage_plan") or "入住前向酒店确认",
        "travel_times": primary.get("platform_reported") or [],
        "action_links": links,
        "backup_name": backup.get("name"),
    }


WEATHER_LINK = action(
    "查看中央气象台预警", "https://www.nmc.cn/publish/alarm.html", "weather", "中央气象台",
    "出发前48小时和每日发车前复核；远期模型只作准备线索",
)


def normalize_weather(item: dict[str, Any]) -> dict[str, Any]:
    links = normalize_actions(item.get("action_links") or [], "weather", "天气服务", "远期预报会变化，临行复核")
    if not any(link.get("type") == "weather" for link in links):
        links.append(WEATHER_LINK)
    warning = item.get("warning") or item.get("warning_status")
    return {**item, "action_links": links, "warning": warning}


IMAGE_BY_ATTRACTION = {
    "qinghai-lake-erlangjian": {
        "url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Qinghai_Lake_%2829033614016%29.jpg?width=1200",
        "alt": "青海湖开阔湖面",
        "source_url": "https://commons.wikimedia.org/wiki/File:Qinghai_Lake_(29033614016).jpg",
        "source_label": "Wikimedia Commons",
        "author": "Sergio Tittarini",
        "license": "CC BY 2.0",
    },
    "chaka-salt-lake": {
        "url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Chaka_Salt_Lake_1.jpg?width=1200",
        "alt": "茶卡盐湖湖面与天空",
        "source_url": "https://commons.wikimedia.org/wiki/File:Chaka_Salt_Lake_1.jpg",
        "source_label": "Wikimedia Commons",
        "author": "AkakiBalanchivadze",
        "license": "CC BY 4.0",
    },
    "mogao-caves": {
        "url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Mogao_Caves_%2842265422972%29.jpg?width=1200",
        "alt": "莫高窟外部建筑与崖体",
        "source_url": "https://commons.wikimedia.org/wiki/File:Mogao_Caves_(42265422972).jpg",
        "source_label": "Wikimedia Commons",
        "author": "David Stanley",
        "license": "CC BY 2.0",
    },
    "mingsha-moon-spring": {
        "url": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Mingsha_Mountain_and_Crescent_Moon_Spring_%2854532735143%29.jpg?width=1200",
        "alt": "鸣沙山与月牙泉",
        "source_url": "https://commons.wikimedia.org/wiki/File:Mingsha_Mountain_and_Crescent_Moon_Spring_(54532735143).jpg",
        "source_label": "Wikimedia Commons",
        "author": "Xiquinho Silva",
        "license": "CC BY 2.0",
    },
}


COMMUNITY_BY_ATTRACTION = {
    "qinghai-lake-erlangjian": [
        {"title": "青甘环线近期体验参考", "source_url": "https://www.xiaohongshu.com/explore/6aafa87f00000000110311fe", "reason": "只参考路线体感和拥挤；本轮只读服务不可用，内容未重新抓取"},
        {"title": "青海湖近期体验参考", "source_url": "https://www.xiaohongshu.com/explore/6aaf9f8c000000002902febb", "reason": "不作为票价、开放或入口依据"},
    ],
    "mingsha-moon-spring": [
        {"title": "鸣沙山近期体验参考", "source_url": "https://www.xiaohongshu.com/explore/6aaf9e970000000026015f1e", "reason": "只参考风沙、排队和体感；官方规则优先"},
    ],
}


ATTR_CONFIG = {
    "qinghai-lake-erlangjian": {"event_id": "e-d2-qinghai", "start": "10:30", "end": "13:00", "weather": "wx-d2-erlangjian-2026-10-02", "area": "海南州共和县", "title": "青海湖二郎剑：先核验，再走官方湖岸线"},
    "chaka-salt-lake": {"event_id": "e-d3-chaka", "start": "07:40", "end": "10:00", "weather": "wx-d3-chaka-2026-10-03", "area": "海西州乌兰县茶卡镇", "title": "茶卡盐湖：用早场完成核心盐湖线"},
    "dachaidan-emerald-lake": {"event_id": "e-d4-emerald", "start": "08:45", "end": "11:15", "weather": "wx-d4-dachaidan-2026-10-04", "area": "海西州大柴旦", "title": "翡翠湖：按开放环线游览，不走野路"},
    "mogao-caves": {"event_id": "e-d5-mogao", "start": "07:30", "end": "12:10", "reference": "08:30", "weather": "wx-d5-dunhuang-2026-10-05", "area": "敦煌莫高窟数字展示中心", "title": "莫高窟：仅在确认 08:30 正常票时执行"},
    "mingsha-moon-spring": {"event_id": "e-d6-mingsha", "start": "15:30", "end": "20:00", "weather": "wx-d6-dunhuang-2026-10-06", "area": "敦煌鸣沙山月牙泉", "title": "鸣沙山月牙泉：傍晚窗口，日落须当天复核"},
}


def make_booking_task(attraction: dict[str, Any]) -> dict[str, Any]:
    config = ATTR_CONFIG[attraction["id"]]
    reservation = attraction.get("reservation") or {}
    official = attraction.get("official") or {}
    is_mogao = attraction["id"] == "mogao-caves"
    is_known_booking = reservation.get("required") is True
    link = reservation.get("booking_url") or official.get("booking_url") or official.get("notice_url")
    link_is_booking = bool(reservation.get("booking_url") or official.get("booking_url"))
    return {
        "id": f"book-{attraction['id']}",
        "title": ("立即查询并购买" if is_mogao else "复核并完成") + attraction["name"] + "预约",
        "product": "2位成人实名票；内部项目按现场风浪、体力和运营另选",
        "quantity": "2人",
        "next_action_at": reservation.get("next_action_at"),
        "deadline": "有合适场次立即下单" if is_mogao else "最迟按景区复核日完成",
        "release_rule": "官方未公布本次日期放票规则" if not is_mogao else "仅以官方预约系统当前可售状态为准",
        "priority": "book_now" if is_mogao else ("book_when_open" if is_known_booking else "recheck_later"),
        "status": reservation.get("status") or "pending",
        "action": reservation.get("action"),
        "event_id": config["event_id"],
        "attraction_id": attraction["id"],
        "action_links": [action(
            "打开官方预约说明" if link_is_booking else "查看开放/预约公告",
            link,
            "official_booking" if link_is_booking else "official_notice",
            attraction["name"] if link_is_booking else "政府/官方公告",
            "核验适用日期、票种、实名要求和退款规则",
        )] if link else [],
    }


def normalize_attraction(attraction: dict[str, Any]) -> dict[str, Any]:
    item = deepcopy(attraction)
    official = item.get("official") or {}
    if item["id"] == "dachaidan-emerald-lake":
        official["homepage_url"] = "https://www.qinghai.gov.cn/zwgk/system/2025/05/20/030072575.shtml"
        official["booking_url"] = None
    elif item["id"] == "qinghai-lake-erlangjian":
        official["booking_url"] = None
    elif item["id"] == "mingsha-moon-spring":
        # The current official page explains the reservation channel but is not
        # itself a checkout page. Preserve that distinction in the UI.
        official["booking_url"] = None
    item["official"] = official
    item["area"] = ATTR_CONFIG[item["id"]]["area"]
    item["visit_duration"] = f"约 {(hm_to_minutes(ATTR_CONFIG[item['id']]['end']) - hm_to_minutes(ATTR_CONFIG[item['id']]['start'])) / 60:g} 小时"
    item["action_links"] = [
        action("导航到官方入口", item["entrance"]["map_url"], "map", "高德地图", "仅使用景区主入口；最终按现场管制进入")
    ]
    return item


def make_attraction_event(attraction: dict[str, Any]) -> dict[str, Any]:
    config = ATTR_CONFIG[attraction["id"]]
    reference = config.get("reference") or config["start"]
    start_ref = hm_to_minutes(reference)
    checkpoints = []
    for index, blueprint in enumerate(attraction.get("checkpoint_blueprint") or [], start=1):
        point_start = start_ref + int(blueprint.get("offset_minutes", 0))
        point_end = point_start + int(blueprint.get("duration_minutes", 0))
        point = {
            "id": f"cp-{attraction['id']}-{index}",
            "order": index,
            "time": minutes_to_hm(point_start),
            "end_time": minutes_to_hm(point_end),
            "kind": "entry" if index == 1 else ("exit" if index == len(attraction["checkpoint_blueprint"]) else "visit"),
            "name": blueprint.get("name"),
            "required": True,
            "instruction": blueprint.get("action"),
            "narration": "这一节点决定后续是否继续；以现场开放范围、排队和体感为准。" if index in {1, 2} else "完成这一核心节点后再决定是否增加可选项目，不为拍照压缩返程缓冲。",
            "move_from_previous": {"mode": "景区官方步行/接驳", "duration": "按现场排队与开放线路"},
            "source_ids": blueprint.get("source_ids") or [],
        }
        if attraction["id"] == "mingsha-moon-spring" and index == 5:
            point["name"] = "临近日落观景/官方活动（条件项）"
            point["instruction"] = "仅在当天日落、风沙、闭园和活动时间均复核后停留；条件不成立就提前离场。"
            point["narration"] = "当前19:16只是远期模型天文值，不能当成承诺；以当天景区公告和天气为准。"
        image = IMAGE_BY_ATTRACTION.get(attraction["id"])
        if image and index == min(3, len(attraction["checkpoint_blueprint"])):
            point["images"] = [image]
        checkpoints.append(point)
    costs = [normalize_cost(item) for item in attraction.get("cost_items") or []]
    baseline = sum(item.get("subtotal_cny") or 0 for item in attraction.get("cost_items") or [] if item.get("pricing_role") == "baseline")
    unknown = any(item.get("subtotal_cny") is None and item.get("pricing_role") in {"baseline", "baseline_if_required"} for item in attraction.get("cost_items") or [])
    reservation = attraction.get("reservation") or {}
    event = {
        "id": config["event_id"],
        "time": config["start"],
        "end_time": config["end"],
        "type": "attraction",
        "attraction_id": attraction["id"],
        "title": config["title"],
        "subtitle": "08:30尚未出票；本卡是条件分支，其他场次必须整体平移" if attraction["id"] == "mogao-caves" else "按入口核验 → 核心必达点 → 原入口离场执行",
        "duration": f"约 {hm_to_minutes(config['end']) - hm_to_minutes(config['start'])} 分钟",
        "area": config["area"],
        "reservation_required": reservation.get("required"),
        "weather_id": config["weather"],
        "admission": {
            "opening_hours": attraction["operations"]["opening_hours"],
            "last_entry": attraction["operations"]["last_entry"],
            "reservation_method": reservation.get("action") or "通过官方渠道核验并实名预约",
            "entry_requirement": attraction["entrance"].get("arrival_instruction"),
            "notice": attraction["operations"].get("temporary_notice"),
        },
        "execution": {
            "entry": {
                "name": attraction["entrance"]["name"],
                "location_query": attraction["entrance"]["location_query"],
                "reason": attraction["entrance"].get("arrival_instruction"),
            },
            "exit": {
                "name": attraction["exit"]["name"],
                "location_query": attraction["entrance"]["location_query"],
            },
            "checkpoints": checkpoints,
            "leave_by": config["end"],
            "fallback": attraction["exit"].get("departure_instruction"),
        },
        "booking_task_ids": [f"book-{attraction['id']}"],
        "cost_items": costs,
        "cost_summary": (f"当前可计入基线：¥{baseline}/2人；" if baseline else "") + ("基础票或必选交通仍有未核价项目" if unknown else "可选项目不计入基线"),
        "preparation": ["身份证原件", "防风保暖层", "防晒与饮水", "出发前再次查看临时公告"],
        "community_refs": COMMUNITY_BY_ATTRACTION.get(attraction["id"], []),
        "action_links": [action("打开入口导航", attraction["entrance"]["map_url"], "map", "高德地图", "按景区正式入口和现场交通组织进入")],
    }
    return event


def transport(event_id: str, start: str, end: str, route_id: str, title: str, subtitle: str = "", weather_id: str | None = None, tips: list[str] | None = None) -> dict[str, Any]:
    event = {"id": event_id, "time": start, "end_time": end, "type": "transport", "route_id": route_id, "title": title, "subtitle": subtitle, "tips": tips or []}
    if weather_id:
        event["weather_id"] = weather_id
    return event


def meal(event_id: str, start: str, end: str, meal_id: str, title: str) -> dict[str, Any]:
    return {"id": event_id, "time": start, "end_time": end, "type": "meal", "meal_id": meal_id, "title": title, "subtitle": "顺路、可替换，不为网红店折返"}


def lodging(event_id: str, start: str, end: str, lodging_id: str, title: str, details: list[str]) -> dict[str, Any]:
    return {"id": event_id, "time": start, "end_time": end, "type": "lodging", "lodging_id": lodging_id, "title": title, "details": details}


def note(event_id: str, start: str, end: str, title: str, details: list[str], tips: list[str] | None = None) -> dict[str, Any]:
    return {"id": event_id, "time": start, "end_time": end, "type": "note", "title": title, "details": details, "tips": tips or []}


def collect_sources() -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for path in sorted((WORKSPACE / "sources").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if str(item.get("url") or "").startswith("https://"):
                merged[item["id"]] = {
                    "id": item["id"], "title": item.get("title"), "url": item.get("url"),
                    "note": item.get("summary") or f"{item.get('authority', '')} · {item.get('kind', '')}",
                    "checked_at": item.get("checked_at"),
                }
    return list(merged.values())


def build() -> dict[str, Any]:
    attractions_result = load("attractions")
    routes_result = load("route-data")
    local_routes_result = load("route-data-local-v2")
    stay_food_result = load("stay-food")
    source_snapshots = load_source_snapshots(routes_result, stay_food_result)
    weather_result = load("weather-risk")
    readiness_result = load("readiness")

    attractions = [normalize_attraction(item) for item in attractions_result["entities"]["attractions"]]
    attraction_map = by_id(attractions)
    attraction_events = {item["id"]: make_attraction_event(item) for item in attractions}
    booking_tasks = [make_booking_task(item) for item in attractions]

    routes = [normalize_route(item) for item in [
        *routes_result["entities"]["transport_edges"],
        *local_routes_result["entities"]["transport_edges"],
    ]]
    routes.extend([
        {
            "id": "main-xnn-to-xining-mercure", "from": "西宁曹家堡国际机场T3航站楼到达层", "to": "西宁海湖新区美居酒店候选可停车入口",
            "mode": "网约车/出租车", "route": "机场大道—G0612/G0611—柴达木路—海湖路—五四西路",
            "distance_meters": 35367, "ride_duration_minutes": 31,
            "door_to_door_duration": "国庆计划45–75分钟，含取行李、候车、市区拥堵和酒店卸行李",
            "cost": "实时车费待查；高德查询显示路桥费约¥6", "reason": "直接到本次住宿候选，避免用中心广场作错误终点",
            "fallback": "主酒店未订成后，按实际酒店入口重新算路", "live_status": "高德2026-09-21基础算路；酒店和航班锁定后重算",
            "map_route": {"origin": "102.049251,36.521815", "destination": "101.723941,36.643921", "mode": "car", "assumption": "终点是住宿候选；实际酒店确定后重算"},
            "action_links": [action("在高德查看机场至候选酒店", "https://uri.amap.com/navigation?from=102.049251%2C36.521815%2C%E8%A5%BF%E5%AE%81T3&to=101.723941%2C36.643921%2C%E8%A5%BF%E5%AE%81%E6%B5%B7%E6%B9%96%E6%96%B0%E5%8C%BA%E7%BE%8E%E5%B1%85%E9%85%92%E5%BA%97&mode=car&policy=0&src=travel-planning&callnative=0", "map", "高德地图", "出发时按实时导航复核")],
            "source_ids": ["route-data-amap-direction", "main-amap-route-corrections-20260921"],
        },
        {
            "id": "main-dachaidan-town-to-dunhuang", "from": "大柴旦镇中心/午餐点", "to": "敦煌市中心临时锚点/最终酒店",
            "mode": "包车＋司机或自驾", "route": "大柴旦镇—G3011柳格高速—当金山—阿克塞—G215—敦煌",
            "distance_meters": 368847, "ride_duration_minutes": 255,
            "door_to_door_duration": "国庆计划345–405分钟，含午餐后上车、正式休息、检查站、施工和酒店卸行李",
            "cost": "计入包车总价或自驾成本，待书面报价；高德查询显示路桥费约¥191", "reason": "午餐已回到大柴旦镇，应从镇内而不是翡翠湖重新起算",
            "fallback": "出现道路管制或预计夜间进入陌生山口时，取消非必要停靠并服从交管/司机方案", "live_status": "高德2026-09-21基础算路；9月30日和出发当天复核",
            "map_route": {"origin": "95.361190,37.849028", "destination": "94.662328,40.142066", "mode": "car", "assumption": "起点为大柴旦镇中心，终点为敦煌市中心临时锚点；酒店确定后重算"},
            "action_links": [action("在高德查看大柴旦镇至敦煌", "https://uri.amap.com/navigation?from=95.361190%2C37.849028%2C%E5%A4%A7%E6%9F%B4%E6%97%A6%E9%95%87&to=94.662328%2C40.142066%2C%E6%95%A6%E7%85%8C%E5%B8%82%E4%B8%AD%E5%BF%83&mode=car&policy=0&src=travel-planning&callnative=0", "map", "高德地图", "出发时按实时导航复核")],
            "source_ids": ["route-data-amap-direction", "main-amap-route-corrections-20260921"],
        },
        {
            "id": "main-chaka-to-keruke-service", "from": "茶卡盐湖景区游客服务中心出口", "to": "中国石化柯鲁克服务区（小柴旦方向）",
            "mode": "包车＋司机或自驾", "route": "茶卡镇—S2013茶德高速—S20德小高速—柯鲁克服务区",
            "distance_meters": 206509, "ride_duration_minutes": 143,
            "door_to_door_duration": "国庆计划165–195分钟，含景区出场、收费站、施工和短休息",
            "cost": "计入包车总价或自驾成本；高德查询显示路桥费约¥90", "reason": "服务区在直达大柴旦主线上，不为午餐驶入都兰县城",
            "fallback": "服务区餐饮不可用时使用茶卡提前打包的主食；仍在服务区完成司机休息", "live_status": "高德2026-09-21基础算路；出发当天复核入口和道路事件",
            "map_route": {"origin": "99.078356,36.759981", "destination": "97.215870,37.341137", "mode": "car", "assumption": "终点为高德标注的小柴旦方向服务区；当天确认同向入口"},
            "action_links": [action("在高德查看茶卡至柯鲁克服务区", "https://uri.amap.com/navigation?from=99.078356%2C36.759981%2C%E8%8C%B6%E5%8D%A1%E7%9B%90%E6%B9%96&to=97.215870%2C37.341137%2C%E6%9F%AF%E9%B2%81%E5%85%8B%E6%9C%8D%E5%8A%A1%E5%8C%BA&mode=car&policy=0&src=travel-planning&callnative=0", "map", "高德地图", "出发时按实时导航复核")],
            "source_ids": ["route-data-amap-direction", "main-amap-route-corrections-20260921"],
        },
        {
            "id": "main-keruke-service-to-dachaidan-hotel", "from": "中国石化柯鲁克服务区（小柴旦方向）", "to": "丽湖雅致大酒店大柴旦候选入口",
            "mode": "包车＋司机或自驾", "route": "柯鲁克服务区—S20德小高速—S314—大柴旦翡翠步行街",
            "distance_meters": 191629, "ride_duration_minutes": 138,
            "door_to_door_duration": "国庆计划170–220分钟，含服务区午休后上车、施工、收费站和酒店卸行李",
            "cost": "计入包车总价或自驾成本；高德查询显示路桥费约¥71", "reason": "与午餐锚点和大柴旦住宿候选一一对应",
            "fallback": "道路延误时取消沿途加点，直接入住；晚餐改酒店或外卖", "live_status": "高德2026-09-21基础算路；酒店确定后替换终点",
            "map_route": {"origin": "97.215870,37.341137", "destination": "95.359818,37.849942", "mode": "car", "assumption": "终点是住宿候选；实际酒店确定后重算"},
            "action_links": [action("在高德查看柯鲁克服务区至大柴旦", "https://uri.amap.com/navigation?from=97.215870%2C37.341137%2C%E6%9F%AF%E9%B2%81%E5%85%8B%E6%9C%8D%E5%8A%A1%E5%8C%BA&to=95.359818%2C37.849942%2C%E5%A4%A7%E6%9F%B4%E6%97%A6%E9%85%92%E5%BA%97%E5%80%99%E9%80%89&mode=car&policy=0&src=travel-planning&callnative=0", "map", "高德地图", "出发时按实时导航复核")],
            "source_ids": ["route-data-amap-direction", "main-amap-route-corrections-20260921"],
        },
    ])
    intercity = deepcopy(routes_result["entities"]["intercity_options"])
    meals = [normalize_meal(item) for item in stay_food_result["entities"]["meal_options"]]
    meal_map = by_id(meals)
    meal_map["meal-d2-dinner-chaka"].update({
        "name": "青盐2号宾馆餐厅/景区门口晚餐", "location": "青盐2号宾馆或景区门口步行范围",
        "why_here": "入住后不再坐车进茶卡镇；优先酒店餐厅或门口即时营业点",
        "fallback": "入住前电话确认酒店留餐；无堂食则在茶卡镇进酒店前打包",
        "action_links": [],
    })
    meal_map["meal-d5-dinner-huyang"].update({
        "name": "酒店/沙洲夜市步行圈焖饼晚餐", "location": "敦煌酒店至沙洲夜市约步行范围内",
        "why_here": "不再专门打车追固定网红店；保留胡羊焖饼这一菜品目标",
        "fallback": "步行圈内选择即时有座的黄焖羊肉/焖饼店，或酒店餐厅",
        "action_links": [action("查看酒店周边焖饼候选", "https://uri.amap.com/search?keyword=%E6%B2%99%E6%B4%B2%E5%A4%9C%E5%B8%82%20%E7%BE%8A%E8%82%89%E7%84%96%E9%A5%BC&city=%E6%95%A6%E7%85%8C&src=travel-planning&callnative=0", "restaurant", "高德地图", "只选步行可达且即时有座的店")],
    })
    meals.append({
        "id": "meal-d3-lunch-main-route", "meal_type": "午餐", "name": "柯鲁克服务区午餐与司机休息",
        "location": "中国石化柯鲁克服务区（德小高速小柴旦方向，POI B0FFGBA1MN）",
        "time_window": "12:45–13:25", "signature_dishes": ["茶卡提前打包的主食", "服务区可用热食", "矿泉水"],
        "per_person": "约¥35–70/人（规划带）", "opening_hours": "高德平台报24小时，餐饮档口仍须2026-10-02晚复核",
        "queue_note": "无热食或排队超过20分钟即吃打包餐；至少保留40分钟给司机用餐和休息",
        "why_here": "位于直达大柴旦主线上，避免都兰方案增加约137公里基础路程",
        "fallback": "茶卡退房时打包主食；服务区只承担停车、如厕和休息",
        "action_links": [action("查看柯鲁克服务区", "https://uri.amap.com/marker?position=97.215870%2C37.341137&name=%E4%B8%AD%E5%9B%BD%E7%9F%B3%E5%8C%96%E6%9F%AF%E9%B2%81%E5%85%8B%E6%9C%8D%E5%8A%A1%E5%8C%BA%28%E5%BE%B7%E5%B0%8F%E9%AB%98%E9%80%9F%E5%B0%8F%E6%9F%B4%E6%97%A6%E6%96%B9%E5%90%91%29&src=travel-planning&coordinate=gaode&callnative=0", "restaurant", "高德地图", "仅确认服务区POI；餐饮档口营业需另查")],
    })
    for day, window in ((2, "06:20–06:50"), (3, "06:30–07:00"), (4, "07:15–07:45"), (5, "06:10–06:35"), (6, "08:00–08:40")):
        meals.append({
            "id": f"meal-d{day}-breakfast", "meal_type": "早餐", "name": "酒店早餐/提前打包",
            "location": "当晚酒店餐厅或前台领取", "time_window": window,
            "signature_dishes": ["鸡蛋", "主食", "水果或酸奶", "温水"],
            "per_person": "含早则0增量；否则约¥20–50/人", "opening_hours": "订房时确认早餐开餐和打包时间",
            "queue_note": "不等现做复杂餐；前一晚预约打包", "why_here": "不增加市内接驳，保证准时出发",
            "fallback": "前一晚便利店准备常温主食、鸡蛋/奶和水", "action_links": [],
        })
    lodgings = [normalize_lodging(item) for item in stay_food_result["entities"]["lodging_options"]]
    weather = [normalize_weather(item) for item in weather_result["entities"]["weather"]]
    readiness = deepcopy(readiness_result["entities"]["readiness"])
    for item in readiness:
        item["action_links"] = normalize_actions(item.get("action_links") or [], "official", "官方/查询平台", "按任务说明复核")

    booking_tasks.extend([
        {
            "id": "book-main-transport", "title": "确认北京→西宁、敦煌→北京大交通", "priority": "book_now", "status": "pending",
            "deadline": "立即查询并出票", "action": "同时比较直飞与铁路；写回实际站点/航站楼、时刻、行李额、含税价和订单状态。",
            "action_links": [
                action("打开12306", "https://www.12306.cn/index/", "rail", "中国铁路12306", "车次、席别、价格和余票以查询时为准"),
                action("打开携程", "https://www.ctrip.com/", "travel_platform", "携程", "航班、酒店和价格以查询时为准"),
            ],
        },
        {
            "id": "book-charter", "title": "取得合规包车与司机书面方案", "priority": "book_now", "status": "pending", "deadline": "2026-09-24前",
            "action": "比较至少两家；合同写明经营主体、营运车辆、驾驶员、保险、油路停、司机食宿、异地返程、超时和取消。",
            "action_links": [action("查看青海旅游客运整治通告", "https://jtyst.qinghai.gov.cn/jtyst/2026-06/04/article_2026060416442445456.html", "official", "青海省交通运输厅", "用作资质与合规核验依据")],
        },
        {
            "id": "book-hotels", "title": "锁定四地可取消住宿", "priority": "book_now", "status": "pending", "deadline": "立即",
            "action": "锁定后把准确地址写回高德路线，并逐店确认早餐、停车、前台和行李寄存。",
            "action_links": [action("打开携程酒店", "https://hotels.ctrip.com/", "hotel", "携程", "选择本次日期、2位成人1间房后查看实时含税价和取消条款")],
        },
    ])

    d1 = [
        transport("e-d1-inbound", "08:00", "15:30", "route-data-beijing-xining-flight", "北京 → 西宁", "优先早班直飞；当前只是占位时间窗，出票后整段重排", "wx-d1-xining-2026-10-01", ["尚未查询实时航班/铁路库存，不把占位时刻视为班次", "如没有合适早班直飞，优先调整D1，不挤压D2睡眠"]),
        transport("e-d1-airport-city", "15:30", "16:45", "main-xnn-to-xining-mercure", "曹家堡机场 → 西宁住宿片区", "取行李后再按最终酒店重算"),
        lodging("e-d1-hotel", "16:45", "17:30", "lodging-xining-night-1", "办理西宁入住", ["主选海湖新区，第二天向西出城更顺", "确认早餐打包、停车和次日07:00装车", "房价和房态尚未实时查询"]),
        meal("e-d1-dinner", "18:30", "20:00", "meal-d1-dinner-xining", "唐道637片区晚餐"),
        note("e-d1-pack", "20:00", "20:30", "把D2随身包单独装好", ["身份证、充电宝、防风防雨层、薄羽绒、饮水放随身包", "与司机复核酒店门口、车辆、D2路况和青海湖开放公告"], ["两位旅行者在不可退预订前确认高海拔、晕车和长途乘车耐受"]),
    ]
    d2 = [
        meal("e-d2-breakfast", "06:20", "06:50", "meal-d2-breakfast", "酒店早餐或提前打包"),
        transport("e-d2-xining-qinghai", "07:00", "10:30", "local-xining-mercure-to-qinghai", "西宁酒店 → 青海湖二郎剑", "国庆按3.5小时上限留足缓冲；退房行李随车", "wx-d2-erlangjian-2026-10-02", ["司机不得行驶中查手机；由乘客查看预警和导航事件"]),
        attraction_events["qinghai-lake-erlangjian"],
        meal("e-d2-lunch", "13:00", "14:00", "meal-d2-lunch-qinghai-lake", "景区出口附近快速午餐"),
        transport("e-d2-qinghai-chaka", "14:00", "18:00", "route-data-qinghai-lake-to-chaka", "青海湖 → 茶卡镇", "当天不硬塞盐湖游览，先入住休息", "wx-d2-chaka-2026-10-02"),
        lodging("e-d2-hotel", "18:00", "18:35", "lodging-chaka-night-2", "办理茶卡入住", ["确认次日07:10退房、行李随车", "前台协助复核盐湖早场开放和入园方式"]),
        meal("e-d2-dinner", "18:45", "20:00", "meal-d2-dinner-chaka", "茶卡镇晚餐"),
    ]
    d3 = [
        meal("e-d3-breakfast", "06:30", "07:00", "meal-d3-breakfast", "酒店早餐或提前打包"),
        transport("e-d3-hotel-chaka", "07:10", "07:40", "local-chaka-qingyan2-to-entrance", "茶卡酒店 → 盐湖游客中心", "退房后带全部行李；尽量赶早场", "wx-d3-chaka-2026-10-03"),
        attraction_events["chaka-salt-lake"],
        transport("e-d3-chaka-west-a", "10:00", "12:45", "main-chaka-to-keruke-service", "茶卡 → 柯鲁克服务区", "走直达大柴旦主线，不为都兰餐厅绕行", "wx-d3-dachaidan-2026-10-03"),
        meal("e-d3-lunch", "12:45", "13:25", "meal-d3-lunch-main-route", "服务区午餐与司机休息"),
        transport("e-d3-chaka-west-b", "13:25", "17:40", "main-keruke-service-to-dachaidan-hotel", "柯鲁克服务区 → 大柴旦酒店候选", "延误时直接入住，不增加沿途景点", "wx-d3-dachaidan-2026-10-03", ["不增加水上雅丹等临时支路", "若19:00后到店，晚餐改酒店或外卖"]),
        lodging("e-d3-hotel", "17:40", "18:10", "lodging-dachaidan-night-3", "办理大柴旦入住", ["确认D4退房装车与翡翠湖入口", "如景区安全开放未确认，D4直接向敦煌出发"]),
        meal("e-d3-dinner", "18:30", "19:50", "meal-d3-dinner-dachaidan", "大柴旦镇晚餐"),
    ]
    d4 = [
        meal("e-d4-breakfast", "07:15", "07:45", "meal-d4-breakfast", "酒店早餐或提前打包"),
        transport("e-d4-hotel-emerald", "08:00", "08:45", "local-dachaidan-lihu-to-emerald", "大柴旦酒店 → 翡翠湖主入口", "退房行李随车；先过安全开放门槛", "wx-d4-dachaidan-2026-10-04"),
        attraction_events["dachaidan-emerald-lake"],
        transport("e-d4-emerald-lunch", "11:15", "12:00", "local-emerald-exit-to-jade-street-lunch", "翡翠湖出口 → 大柴旦午餐", "回镇吃热食并给司机留休息", "wx-d4-dachaidan-2026-10-04"),
        meal("e-d4-lunch", "12:00", "12:50", "meal-d4-lunch-dachaidan", "大柴旦镇午餐"),
        transport("e-d4-dachaidan-dunhuang", "13:00", "19:45", "main-dachaidan-town-to-dunhuang", "大柴旦 → 敦煌", "13:00为最晚发车；跨青甘长途段不增加景点", "wx-d4-dunhuang-2026-10-04", ["15:40–16:00在有人值守服务区完成司机休息与如厕", "若11:15仍未离开翡翠湖，立即结束游览并压缩午餐，不以赶点挤压司机休息", "出现封路、结冰或大风管制即按交管/司机方案停留或改线"]),
        lodging("e-d4-hotel", "19:45", "20:15", "lodging-dunhuang-nights-4-6", "办理敦煌连住三晚", ["连住减少搬运行李", "立即复核莫高窟订单、次日07:30上车和早餐打包"]),
        meal("e-d4-dinner", "20:15", "21:15", "meal-d4-dinner-dunhuang", "酒店附近快速晚餐"),
    ]
    d5 = [
        meal("e-d5-breakfast", "06:10", "06:35", "meal-d5-breakfast", "打包早餐"),
        transport("e-d5-hotel-mogao", "06:45", "07:30", "local-dunhuang-hotel-to-mogao", "敦煌酒店 → 莫高窟数字展示中心", "按08:30票倒排，至少提前30分钟到", "wx-d5-dunhuang-2026-10-05"),
        attraction_events["mogao-caves"],
        transport("e-d5-mogao-lunch", "12:10", "13:05", "local-mogao-exit-to-daji-lunch", "莫高窟 → 敦煌市区午餐", "完成官方摆渡回数字中心后再上车", "wx-d5-dunhuang-2026-10-05"),
        meal("e-d5-lunch", "13:15", "14:30", "meal-d5-lunch-yellow-noodles", "驴肉黄面午餐"),
        transport("e-d5-lunch-hotel", "14:30", "14:50", "local-daji-lunch-to-dunhuang-hotel", "午餐点 → 酒店", "回房休息，不再塞景点"),
        {"id": "e-d5-rest", "time": "15:00", "end_time": "17:30", "type": "rest", "title": "午休与整理", "details": ["连续三天长途后主动留空", "复核D6风沙、鸣沙山公告和预约订单"]},
        meal("e-d5-dinner", "18:30", "20:00", "meal-d5-dinner-huyang", "胡羊焖饼晚餐"),
    ]
    d6 = [
        meal("e-d6-breakfast", "08:00", "08:40", "meal-d6-breakfast", "酒店早餐"),
        {"id": "e-d6-rest", "time": "09:00", "end_time": "11:30", "type": "rest", "title": "睡足、洗衣与补给", "details": ["上午不排远途景点", "补齐饮水、防晒、手机防沙袋和薄外套"]},
        meal("e-d6-lunch", "12:00", "13:15", "meal-d6-lunch-dunhuang", "鸣沙山前清淡午餐"),
        transport("e-d6-hotel-mingsha", "14:30", "15:30", "local-dunhuang-hotel-to-mingsha", "敦煌酒店 → 鸣沙山中门", "给单向道路、停车和入园排队留足时间", "wx-d6-dunhuang-2026-10-06"),
        attraction_events["mingsha-moon-spring"],
        transport("e-d6-mingsha-hotel", "20:00", "20:50", "local-mingsha-to-dunhuang-hotel", "鸣沙山中门 → 酒店/晚餐片区", "避开散场峰值；找车困难时原地等候", "wx-d6-dunhuang-2026-10-06"),
        meal("e-d6-dinner", "20:50", "22:00", "meal-d6-dinner-after-mingsha", "返城后的灵活晚餐"),
    ]
    d7 = [
        meal("e-d7-breakfast", "07:00", "07:35", "meal-d7-departure-flex", "酒店早餐或打包早餐"),
        lodging("e-d7-checkout", "07:35", "08:00", "lodging-dunhuang-nights-4-6", "退房并核对全部行李", ["贵重物品随身", "按实际航班/列车倒推；本时间窗需出票后改写"]),
        transport("e-d7-airport", "08:00", "09:00", "route-data-dunhuang-to-dnh", "敦煌酒店 → 莫高国际机场", "以下按11:00假设起飞演示；出票后重排", "wx-d7-dunhuang-2026-10-07"),
        note("e-d7-checkin", "09:00", "11:00", "值机、托运与安检缓冲", ["只用于说明机场到达与起飞之间必须留足时间", "具体值机截止、航站楼和行李额以票面/承运人为准"]),
        transport("e-d7-return", "11:00", "19:00", "route-data-dunhuang-beijing-flight", "敦煌 → 北京", "优先直飞，同票中转次选；当前只是占位时间窗", "wx-d7-dunhuang-2026-10-07", ["未查询实时航班/铁路库存，不把占位时刻视为班次", "无合适航班时再比较12306铁路方案"]),
    ]

    days = [
        {"date": "2026-10-01", "label": "D1 · 周四", "title": "抵达西宁", "summary": "只完成进城、入住和适应，不把第一天排满", "cost_summary": "大交通、接机、酒店待实时查询；晚餐按¥50–110/人规划", "meal_exemptions": {"午餐": "实际航班未出票；午餐按机场/机上时刻解决，出票后补成独立事件"}, "events": d1},
        {"date": "2026-10-02", "label": "D2 · 周五", "title": "西宁 → 青海湖 → 茶卡", "summary": "先完成青海湖核心线，傍晚只转场不赶盐湖", "cost_summary": "青海湖票和内部项目待官方国庆公告；包车待书面报价", "events": d2},
        {"date": "2026-10-03", "label": "D3 · 周六", "title": "茶卡盐湖 → 大柴旦", "summary": "早场游盐湖，经柯鲁克服务区沿约398公里主线西行", "cost_summary": "强制门票¥120/2人；建议单程小火车另¥100/2人，其他项目可选", "events": d3},
        {"date": "2026-10-04", "label": "D4 · 周日", "title": "翡翠湖 → 敦煌", "summary": "上午景区，下午完成全程最长转场之一", "cost_summary": "翡翠湖票和内部交通待核；长途车费计入包车待报价", "events": d4},
        {"date": "2026-10-05", "label": "D5 · 周一", "title": "莫高窟与恢复日", "summary": "以下时间轴仅在确认08:30正常票时成立；其他票面时间整体重排", "cost_summary": "正常票官方价¥476/2人；应急票是内容不同的互斥备选", "events": d5},
        {"date": "2026-10-06", "label": "D6 · 周二", "title": "鸣沙山月牙泉", "summary": "上午留白，下午按风沙和日落条件执行", "cost_summary": "门票和骆驼/观光车等内部项目待国庆公告与现场核验", "events": d6},
        {"date": "2026-10-07", "label": "D7 · 周三", "title": "敦煌返北京", "summary": "完全服从实际出票时刻，页面时间只是编排占位", "cost_summary": "返程票、送机和行李费用待实时查询", "meal_exemptions": {"午餐": "实际返程未出票；按机场/机上时刻解决，出票后补成独立事件", "晚餐": "19:00只是占位抵达；按实际航班的机上餐或抵京时间安排"}, "events": d7},
    ]

    return {
        "trip": {
            "title": "青甘大环线 · 7天执行版",
            "subtitle": "北京出发｜青海湖、茶卡、大柴旦、敦煌｜2位年轻成人",
            "destination": "青海—甘肃",
            "date_range": "2026-10-01 — 2026-10-07",
            "travelers": "2 位成人",
            "budget": "预算待实时交通、住宿与包车报价后确定",
            "currency": "CNY",
            "updated_at": "2026-09-21",
            "assumptions": [
                "主方案为北京飞西宁、当地合规包车+司机、敦煌飞北京；实际班次尚未实时查询，D1/D7时间是编排占位。",
                "不采用都兰午餐绕行：该方案约535公里基础路程，较茶卡直达大柴旦约398公里多约137公里；午餐改为主路正规停靠点。",
                "国庆开放、停检、预约、房态、道路和天气均设复核点；未核得的数据明确标为待确认。",
                "小红书仅作为体感与避坑参考；本轮只读服务不可用，未重新抓取，也不复制受限图片。",
                "当前已核强制门票为茶卡¥120/2人 + 莫高窟正常票¥476/2人，共¥596/2人；茶卡单程小火车建议项另加¥100/2人。",
            ],
        },
        "workflow": {
            "phase": "confirmed_planning",
            "selected_route_id": "route_a_essence_7d",
            "confirmed_at": "2026-09-21T00:00:00+08:00",
            "pending_confirmations": ["去程与返程出票", "包车主体/车辆/司机/合同", "四地酒店", "两人高海拔与晕车耐受", "景区国庆公告与预约"],
        },
        "route_proposals": [{"id": "route_a_essence_7d", "title": "青甘核心7日线", "cities": ["西宁", "茶卡", "大柴旦", "敦煌"], "pace": "中高强度，D3/D4长途", "status": "confirmed"}],
        "planning": {
            "route_strategy": "西宁进、敦煌出，核心景点顺向串联；砍掉张掖、嘉峪关、祁连和水上雅丹，避免7天内反复折返。",
            "inventory_contract_version": 1,
            "source_snapshots": source_snapshots,
            "readiness": readiness,
            "attractions": attractions,
            "transport_edges": routes,
            "intercity_options": intercity,
            "lodging_options": lodgings,
            "meal_options": meals,
            "weather": weather,
            "budget": {
                "currency": "CNY",
                "items": [
                    {"category": "已核强制门票", "per_person": "¥298/人", "group": "¥596/2人", "status": "partial_verified"},
                    {"category": "建议内部交通", "per_person": "茶卡单程小火车¥50/人", "group": "¥100/2人，非强制", "status": "official_published"},
                    {"category": "餐饮", "per_person": "约¥495–1360/人", "group": "约¥990–2720/2人（含早时早餐按0增量）", "status": "estimated"},
                    {"category": "大交通/包车/住宿", "per_person": "待实时查询与书面报价", "group": "未计入总额", "status": "to_recheck"},
                ],
                "total_per_person": "当前不能形成可信总价；完成出票、酒店和包车报价后自动汇总",
                "excludes": ["可选内部项目", "个人购物", "临时改线和医疗支出"],
            },
            "booking_tasks": booking_tasks,
            "alternatives": [
                {"trigger": "翡翠湖未确认安全开放", "replace_event_ids": ["e-d4-emerald", "e-d4-emerald-lunch"], "plan": "取消景区，早餐后直接向敦煌出发；不改去无资质荒漠点。"},
                {"trigger": "鸣沙山大风/沙尘/活动取消", "replace_event_ids": ["e-d6-mingsha"], "plan": "留在敦煌市区安排室内文化活动或休息；不追日落。"},
                {"trigger": "莫高窟正常票无票", "replace_event_ids": ["e-d5-mogao"], "plan": "只在官方系统比较应急票或10月6日上午备选，不接受第三方代抢。"},
                {"trigger": "莫高窟取得非08:30正常票", "replace_event_ids": ["e-d5-hotel-mogao", "e-d5-mogao", "e-d5-mogao-lunch", "e-d5-lunch"], "plan": "以票面时间为T0：酒店最晚T0-90分钟出发，T0-30分钟到数字中心；电影、摆渡、洞窟和返城整体等量平移。若只取得应急票，必须按官方应急流程重建洞窟数量、时长和费用，不能套用本卡。"},
            ],
            "excluded_attractions": [
                {"name": "张掖/嘉峪关/祁连", "reason": "7天内加入会导致明显折返并压缩莫高窟、睡眠和返程缓冲"},
                {"name": "水上雅丹", "reason": "会改变大柴旦至敦煌主线；未完成道路、工时与替代成本核验"},
            ],
        },
        "days": days,
        "sources": collect_sources(),
    }


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    target = ARTIFACTS / "itinerary.json"
    target.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成：{target}")


if __name__ == "__main__":
    main()
