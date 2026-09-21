from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "travel-planning"
MODULE_PATH = SKILL_ROOT / "scripts" / "render_itinerary.py"
SPEC = importlib.util.spec_from_file_location("render_itinerary", MODULE_PATH)
assert SPEC and SPEC.loader
render_itinerary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_itinerary)


def add_inventory_binding(data: dict, expires_at: str = "2099-01-01T10:30:00+08:00") -> str:
    snapshot_id = "0123456789abcdef01234567"
    data["planning"]["source_snapshots"] = [{
        "schema_version": "travel-source-snapshot/v1", "snapshot_id": snapshot_id,
        "snapshot_kind": "quote", "status": "platform_reported",
        "provider": {"id": "fliggy_flyai", "name": "飞猪 FlyAI"},
        "product_type": "train", "tool": "search-train", "query": {"dep_date": "2026-10-17"},
        "freshness": {"checked_at": "2026-09-21T10:00:00+08:00", "expires_at": expires_at, "dynamic": True},
        "items": [{
            "offer_id": "g1234-second", "name": "G1234",
            "price": {"amount": 73, "currency": "CNY", "display": "¥73", "basis": "per_adult"},
            "availability": {"status": "provider_returned", "remaining": None},
            "action_link": "https://example.com/train/g1234",
        }],
        "count": 1, "raw_response_hash": "sha256:" + "a" * 64,
        "source": {"title": "飞猪", "url": "https://example.com", "kind": "official_platform_api"},
        "disclaimer": "下单前复核",
    }]
    route = next(item for item in data["planning"]["transport_edges"] if item["id"] == "r1")
    route["inventory_refs"] = [{"snapshot_id": snapshot_id, "offer_id": "g1234-second", "role": "candidate_quote"}]
    return snapshot_id


class RenderItineraryTest(unittest.TestCase):
    def load_example(self) -> dict:
        return json.loads((SKILL_ROOT / "assets" / "example-itinerary.json").read_text(encoding="utf-8"))

    def test_readiness_is_rendered(self) -> None:
        html = render_itinerary.build(self.load_example())
        self.assertIn("西湖经典线", html)
        self.assertNotIn("先研究，再排行程", html)
        self.assertNotIn("天气与复核", html)

    def test_bound_inventory_snapshot_is_validated_and_rendered_in_event(self) -> None:
        data = self.load_example()
        add_inventory_binding(data)
        html = render_itinerary.build(data)
        self.assertIn("实时酒旅来源", html)
        self.assertIn("飞猪 FlyAI · G1234", html)
        self.assertIn("查看供应商结果", html)

    def test_inventory_binding_rejects_offer_from_another_snapshot(self) -> None:
        data = self.load_example()
        add_inventory_binding(data)
        route = next(item for item in data["planning"]["transport_edges"] if item["id"] == "r1")
        route["inventory_refs"][0]["offer_id"] = "not-in-snapshot"
        with self.assertRaisesRegex(ValueError, "offer_id 不属于引用快照"):
            render_itinerary.validate_data(data)

    def test_to_recheck_readiness_requires_action_link(self) -> None:
        data = self.load_example()
        data["planning"]["readiness"][0]["action_links"] = []
        with self.assertRaisesRegex(ValueError, "必须提供 action_links"):
            render_itinerary.validate_data(data)

    def test_rejects_non_https_action_anywhere(self) -> None:
        data = self.load_example()
        data["planning"]["booking_tasks"][0]["action_links"] = [
            {"label": "bad", "url": "http://example.com"}
        ]
        with self.assertRaisesRegex(ValueError, "必须使用 HTTPS"):
            render_itinerary.validate_data(data)

    def test_attraction_costs_render_inside_event(self) -> None:
        data = self.load_example()
        event = data["days"][0]["events"][1]
        event["admission"]["opening_hours"] = "08:00–18:00"
        event["admission"]["last_entry"] = "17:30"
        event["cost_items"] = [{
            "name": "基础门票",
            "kind": "base_ticket",
            "unit_price": "80元/人",
            "quantity": "2人",
            "subtotal": "160元/2人",
            "pricing_role": "baseline",
            "required": True,
            "status": "official_confirmed",
            "source_ids": ["s1"],
        }]
        event["cost_summary"] = "基线160元/2人"
        html = render_itinerary.build(data)
        self.assertIn("费用明细", html)
        self.assertIn("160元/2人", html)
        self.assertIn("08:00–18:00", html)
        self.assertIn("17:30", html)

    def test_confirmed_attraction_requires_base_ticket_in_event(self) -> None:
        data = self.load_example()
        attraction_event = data["days"][0]["events"][1]
        attraction_event.pop("cost_items", None)
        with self.assertRaisesRegex(ValueError, "基础门票 cost_items"):
            render_itinerary.validate_data(data)

    def test_event_facts_are_labeled_instead_of_rendered_as_chips(self) -> None:
        html = render_itinerary.build(self.load_example())
        self.assertIn("建议游览时长", html)
        self.assertIn("所在区域", html)
        self.assertIn("开放与预约", html)
        self.assertIn("预约方式", html)
        self.assertNotIn('class="chip"', html)
        self.assertNotIn('class="chips"', html)

    def test_attraction_renders_checkpoints_and_not_report_reason(self) -> None:
        html = render_itinerary.build(self.load_example())
        self.assertIn("景区内怎么玩", html)
        self.assertIn("湖滨公园湖岸", html)
        self.assertIn("10:30 前从这里离开", html)
        self.assertIn("现场看点", html)
        self.assertNotIn("安排理由", html)

    def test_weather_is_a_corner_link_not_a_fact_row(self) -> None:
        html = render_itinerary.build(self.load_example())
        self.assertIn('class="weather-badge"', html)
        self.assertIn("查看杭州西湖天气", html)
        self.assertIn("https://www.weather.com.cn/weather/101210101.shtml", html)
        self.assertNotIn("<dt>天气影响</dt>", html)

    def test_checkpoint_can_embed_meal_research(self) -> None:
        html = render_itinerary.build(self.load_example())
        self.assertIn("途中补给 · 龙井村途中茶歇", html)
        self.assertIn("龙井茶、桂花糕", html)

    def test_confirmed_attraction_requires_executable_checkpoints(self) -> None:
        data = self.load_example()
        data["days"][0]["events"][1].pop("execution")
        with self.assertRaisesRegex(ValueError, "execution.entry"):
            render_itinerary.validate_data(data)

    def test_confirmed_attraction_requires_structured_admission(self) -> None:
        data = self.load_example()
        data["days"][0]["events"][1]["admission"].pop("last_entry")
        with self.assertRaisesRegex(ValueError, "admission 缺少字段"):
            render_itinerary.validate_data(data)

    def test_confirmed_attraction_requires_separate_official_endpoints(self) -> None:
        data = self.load_example()
        data["planning"]["attractions"][0]["official"].pop("notice_url")
        with self.assertRaisesRegex(ValueError, "official 缺少字段"):
            render_itinerary.validate_data(data)

    def test_admission_panel_renders_official_notice_link(self) -> None:
        html = render_itinerary.build(self.load_example())
        self.assertIn("景区官网", html)
        self.assertIn("临时公告", html)
        self.assertIn("出发前准备", html)

    def test_checkpoint_requires_internal_time_range(self) -> None:
        data = self.load_example()
        data["days"][0]["events"][1]["execution"]["checkpoints"][0].pop("end_time")
        with self.assertRaisesRegex(ValueError, r"checkpoint\[0\] 缺少字段"):
            render_itinerary.validate_data(data)

    def test_weather_requires_viewable_weather_link(self) -> None:
        data = self.load_example()
        data["planning"]["weather"][0]["action_links"][0]["type"] = "source"
        with self.assertRaisesRegex(ValueError, "weather 类型的查看入口"):
            render_itinerary.validate_data(data)

    def test_meal_research_is_rendered_in_timeline(self) -> None:
        html = render_itinerary.build(self.load_example())
        self.assertIn("去哪里", html)
        self.assertIn("片儿川、小笼", html)
        self.assertIn("为什么顺路", html)
        self.assertIn("超过 20 分钟改用备选", html)

    def test_meal_candidate_cards_show_sources_routes_and_backups(self) -> None:
        html = render_itinerary.build(self.load_example())
        self.assertIn("餐厅候选", html)
        self.assertIn("灵隐杭帮面馆 A", html)
        self.assertIn("灵隐杭帮面馆 B", html)
        self.assertIn("主选", html)
        self.assertIn("备选 1", html)
        self.assertIn("4.6/5 · 820条评价", html)
        self.assertIn("<b>小红书</b> · 3 篇参考", html)
        self.assertIn("候选总计22分钟 · 基准18分钟 · 额外绕行4分钟", html)
        self.assertIn("查看上一站到餐厅路线", html)
        self.assertIn("查看餐厅到下一站路线", html)
        self.assertIn("查看灵隐杭帮面馆 A 官方相册", html)
        self.assertIn("https://www.xiaohongshu.com/explore/demo-lingyin-a-1", html)

    def test_embedded_checkpoint_meal_renders_full_candidate(self) -> None:
        html = render_itinerary.build(self.load_example())
        self.assertIn("途中补给 · 龙井村途中茶歇", html)
        self.assertIn("龙井村茶歇点", html)
        self.assertIn("候选总计6分钟 · 基准5分钟 · 额外绕行1分钟", html)
        self.assertIn("未取得可核验近期内容", html)

    def test_normal_meal_requires_two_to_three_candidates(self) -> None:
        data = self.load_example()
        meal = data["planning"]["meal_options"][0]
        meal["candidate_ids"] = [meal["candidate_ids"][0]]
        with self.assertRaisesRegex(ValueError, "2至3个餐厅候选"):
            render_itinerary.validate_data(data)

    def test_every_candidate_must_fit_detour_constraint(self) -> None:
        data = self.load_example()
        evaluation = data["planning"]["meal_route_evaluations"][1]
        evaluation["total_door_to_door_minutes"] = 34
        evaluation["detour_minutes"] = 16
        evaluation["to_next"]["door_to_door_minutes"] = 23
        with self.assertRaisesRegex(ValueError, "超过本餐最大允许绕行"):
            render_itinerary.validate_data(data)

    def test_route_detour_must_use_same_baseline(self) -> None:
        data = self.load_example()
        data["planning"]["meal_route_evaluations"][0]["detour_minutes"] = 7
        with self.assertRaisesRegex(ValueError, "额外绕行必须等于"):
            render_itinerary.validate_data(data)

    def test_platform_signal_requires_rating_and_review_count_or_unavailable_reason(self) -> None:
        data = self.load_example()
        signal = data["planning"]["restaurant_snapshots"][0]["platform_signals"][0]
        signal["review_count"] = None
        with self.assertRaisesRegex(ValueError, "评分和评价量"):
            render_itinerary.validate_data(data)

    def test_restaurant_community_consensus_requires_original_note_links(self) -> None:
        data = self.load_example()
        community = data["planning"]["restaurant_snapshots"][0]["community_consensus"]
        community["references"] = community["references"][:1]
        with self.assertRaisesRegex(ValueError, "社区统计与原帖明细不一致|至少3条近期社区参考及原帖链接"):
            render_itinerary.validate_data(data)

    def test_restaurant_media_requires_original_source(self) -> None:
        data = self.load_example()
        data["planning"]["restaurants"][0]["media"][0].pop("source_url")
        with self.assertRaisesRegex(ValueError, "链接预览.*缺少来源"):
            render_itinerary.validate_data(data)

    def test_embedded_meal_is_subject_to_v3_route_gate(self) -> None:
        data = self.load_example()
        data["planning"]["meal_route_evaluations"][-1].pop("baseline_door_to_door_minutes")
        with self.assertRaisesRegex(ValueError, "缺少可比较的数值路线耗时"):
            render_itinerary.validate_data(data)

    def test_restaurant_rejects_vague_location_and_fake_poi(self) -> None:
        data = self.load_example()
        location = data["planning"]["restaurants"][0]["location"]
        location.update({"physical_address": "景区附近", "coordinates": "附近", "poi_id": "unknown"})
        with self.assertRaisesRegex(ValueError, "坐标.*lng,lat|完整门牌地址|真实平台 POI"):
            render_itinerary.validate_data(data)

    def test_restaurant_candidates_cannot_duplicate_same_poi(self) -> None:
        data = self.load_example()
        data["planning"]["restaurants"][1]["location"]["poi_id"] = data["planning"]["restaurants"][0]["location"]["poi_id"]
        with self.assertRaisesRegex(ValueError, "重复餐厅实体"):
            render_itinerary.validate_data(data)

    def test_restaurant_poi_must_match_map_source_evidence(self) -> None:
        data = self.load_example()
        data["planning"]["restaurants"][0]["location"]["poi_id"] = "FAKE-POI-123"
        with self.assertRaisesRegex(ValueError, "POI 与地图来源证据不一致"):
            render_itinerary.validate_data(data)

    def test_meal_requires_numeric_max_detour(self) -> None:
        data = self.load_example()
        data["planning"]["meal_options"][0]["constraints"].pop("max_detour_minutes")
        with self.assertRaisesRegex(ValueError, "数值 max_detour_minutes"):
            render_itinerary.validate_data(data)

    def test_unavailable_community_requires_search_and_manual_recheck(self) -> None:
        data = self.load_example()
        data["planning"]["restaurant_snapshots"][-1]["community_consensus"].pop("query_runs")
        with self.assertRaisesRegex(ValueError, "社区不可用时必须记录查询"):
            render_itinerary.validate_data(data)

    def test_community_reference_requires_recent_authored_original(self) -> None:
        data = self.load_example()
        reference = data["planning"]["restaurant_snapshots"][0]["community_consensus"]["references"][0]
        reference.pop("author")
        with self.assertRaisesRegex(ValueError, "社区原帖缺少 ID、作者"):
            render_itinerary.validate_data(data)

    def test_meal_route_must_reference_shared_baseline(self) -> None:
        data = self.load_example()
        data["planning"]["meal_route_evaluations"][0]["baseline_route_id"] = "made-up-baseline"
        with self.assertRaisesRegex(ValueError, "统一 baseline route"):
            render_itinerary.validate_data(data)

    def test_restaurant_sources_must_exist_in_registry(self) -> None:
        data = self.load_example()
        data["planning"]["restaurants"][0]["source_ids"] = ["missing-source"]
        with self.assertRaisesRegex(ValueError, "不存在的 source_ids"):
            render_itinerary.validate_data(data)

    def test_embedded_meal_rejects_unverified_platform_signal(self) -> None:
        data = self.load_example()
        snapshot = data["planning"]["restaurant_snapshots"][-1]
        snapshot["platform_signals"][0]["status"] = "unavailable"
        snapshot["platform_signals"][0].pop("unavailable_reason", None)
        with self.assertRaisesRegex(ValueError, "景点节点.*未取得评分时必须说明原因"):
            render_itinerary.validate_data(data)

    def test_embedded_meal_snapshot_must_match_trip_date(self) -> None:
        data = self.load_example()
        data["planning"]["restaurant_snapshots"][-1]["applicable_date"] = "2026-10-19"
        with self.assertRaisesRegex(ValueError, "景点节点.*动态快照日期或用餐时段不一致"):
            render_itinerary.validate_data(data)

    def test_confirmed_meal_requires_research_reference(self) -> None:
        data = self.load_example()
        data["days"][0]["events"][3].pop("meal_id")
        with self.assertRaisesRegex(ValueError, "必须引用有效的 meal_id"):
            render_itinerary.validate_data(data)

    def test_required_booking_is_bound_to_attraction_event(self) -> None:
        data = self.load_example()
        event = data["days"][0]["events"][1]
        event["reservation_required"] = True
        data["planning"]["attractions"][0]["official"]["booking_url"] = "https://westlake.hangzhou.gov.cn/"
        with self.assertRaisesRegex(ValueError, "必须提供 booking_task_ids"):
            render_itinerary.validate_data(data)

    def test_required_booking_accepts_official_channel_guidance(self) -> None:
        data = self.load_example()
        event = data["days"][0]["events"][1]
        event["reservation_required"] = True
        official = data["planning"]["attractions"][0]["official"]
        official["booking_url"] = None
        official["booking_status"] = "official_channel_listed"
        event["booking_task_ids"] = ["b1"]
        data["planning"]["booking_tasks"][0]["event_id"] = event["id"]
        data["planning"]["booking_tasks"][0]["attraction_id"] = event["attraction_id"]
        render_itinerary.validate_data(data)

    def test_attraction_legacy_details_do_not_duplicate_checkpoint_timeline(self) -> None:
        data = self.load_example()
        attraction_event = data["days"][0]["events"][1]
        attraction_event["details"] = ["唯一执行细节"]
        attraction_event["tips"] = ["唯一注意事项"]
        html = render_itinerary.build(data)
        self.assertNotIn("唯一执行细节", html)
        self.assertNotIn("唯一注意事项", html)
        self.assertIn("景区内怎么玩", html)

    def test_missing_event_images_do_not_create_fake_placeholders(self) -> None:
        data = self.load_example()
        for day in data["days"]:
            for event in day["events"]:
                event.pop("images", None)
        html = render_itinerary.build(data)
        self.assertNotIn("image-placeholder", html)
        self.assertNotIn("图片占位", html)

    def test_real_event_image_is_rendered_when_present(self) -> None:
        data = self.load_example()
        data["days"][0]["events"][1]["images"] = [{
            "url": "https://example.com/west-lake.jpg",
            "alt": "西湖实景",
            "source_url": "https://commons.wikimedia.org/wiki/File:West_Lake.jpg",
            "source_label": "Wikimedia Commons",
            "author": "示例作者",
            "license": "CC BY 4.0",
        }]
        html = render_itinerary.build(data)
        self.assertIn('src="https://example.com/west-lake.jpg"', html)
        self.assertIn('alt="西湖实景"', html)
        self.assertIn("Wikimedia Commons · 示例作者 · CC BY 4.0", html)

    def test_checkpoint_image_is_rendered_next_to_its_stop(self) -> None:
        data = self.load_example()
        data["days"][0]["events"][1]["execution"]["checkpoints"][0]["images"] = [{
            "url": "https://example.com/lakefront.jpg",
            "alt": "湖滨公园湖岸示意",
            "source_url": "https://commons.wikimedia.org/",
            "source_label": "Wikimedia Commons",
            "author": "示例作者",
            "license": "CC BY 4.0",
        }]
        html = render_itinerary.build(data)
        self.assertIn('class="checkpoint-images"', html)
        self.assertIn("湖滨公园湖岸示意", html)

    def test_xiaohongshu_reference_renders_as_link_card_not_hotlinked_image(self) -> None:
        data = self.load_example()
        data["days"][0]["events"][1]["community_refs"] = [{
            "title": "西湖近期体验",
            "author": "旅行者",
            "source_url": "https://www.xiaohongshu.com/explore/example-note",
            "interactions": {"likes": "12", "comments": "3", "collections": "8"},
            "reason": "用于判断周末拥挤程度",
        }]
        html = render_itinerary.build(data)
        self.assertIn("小红书近期体验参考", html)
        self.assertIn("西湖近期体验", html)
        self.assertIn("https://www.xiaohongshu.com/explore/example-note", html)
        self.assertNotIn("xhscdn.com", html)

    def test_transport_route_embeds_no_key_amap_route_page(self) -> None:
        data = self.load_example()
        route = data["planning"]["transport_edges"][0]
        route["map_route"] = {
            "origin": "120.100000,30.200000",
            "destination": "120.200000,30.300000",
            "mode": "car",
        }
        route["action_links"] = [{
            "type": "map",
            "label": "在高德查看完整路线",
            "provider": "高德地图",
            "url": "https://uri.amap.com/navigation?from=120.1,30.2,start&to=120.2,30.3,end&mode=walk",
        }]
        html = render_itinerary.build(data)
        self.assertIn('class="route-map-frame"', html)
        self.assertIn('data-src="https://ditu.amap.com/dir?', html)
        self.assertIn('data-mobile-src="https://m.amap.com/navigation/carmap/', html)
        self.assertIn("saddr=120.100000,30.200000,", html)
        self.assertIn("daddr=120.200000,30.300000,", html)
        self.assertIn("sort=dist", html)
        self.assertNotIn("security-code", html)
        self.assertIn("const mapObserver=new IntersectionObserver", html)
        self.assertIn("navigator.userAgentData?.mobile", html)
        self.assertIn('class="route-map-fullscreen"', html)
        self.assertIn("requestFullscreen", html)
        self.assertIn("document.fullscreenElement", html)
        self.assertIn("allowfullscreen", html)
        self.assertIn(".route-map-frame{height:220px}", html)
        self.assertIn("@media(max-width:620px){.route-map-controls{width:100%;justify-content:space-between}.route-map-frame{height:180px}}", html)
        self.assertIn("在高德查看完整路线", html)

    def test_non_driving_route_keeps_general_amap_page(self) -> None:
        data = self.load_example()
        route = data["planning"]["transport_edges"][0]
        route["map_route"] = {
            "origin": "120.100000,30.200000",
            "destination": "120.200000,30.300000",
            "mode": "walk",
        }
        html = render_itinerary.amap_embed_url(route)
        self.assertIn("https://ditu.amap.com/dir?", html)
        self.assertIn("type=walk", html)
        self.assertEqual(render_itinerary.amap_mobile_embed_url(route), html)

    def test_transport_route_keeps_link_without_map_coordinates(self) -> None:
        data = self.load_example()
        route = data["planning"]["transport_edges"][0]
        route["map_route"] = {}
        route["action_links"] = [{
            "type": "map",
            "label": "在高德查看完整路线",
            "provider": "高德地图",
            "url": "https://uri.amap.com/navigation?from=120.1,30.2,start&to=120.2,30.3,end&mode=walk",
        }]
        html = render_itinerary.render_route_map(route)[0]
        self.assertNotIn('class="route-map-frame"', html)
        self.assertIn("在高德查看完整路线", html)

    def test_confirmed_local_transport_requires_map_coordinates_and_link(self) -> None:
        data = self.load_example()
        route = data["planning"]["transport_edges"][0]
        route.pop("map_route")
        with self.assertRaisesRegex(ValueError, "必须提供 map_route"):
            render_itinerary.validate_data(data)

        data = self.load_example()
        route = data["planning"]["transport_edges"][0]
        route["action_links"] = []
        with self.assertRaisesRegex(ValueError, "高德 URI 路线 action_link"):
            render_itinerary.validate_data(data)

        data = self.load_example()
        route = data["planning"]["transport_edges"][0]
        route["map_route"]["mode"] = "spaceship"
        with self.assertRaisesRegex(ValueError, "car、bus 或 walk"):
            render_itinerary.validate_data(data)

        data = self.load_example()
        route = data["planning"]["transport_edges"][0]
        route["action_links"][0]["url"] = "https://example.com/not-an-amap-route"
        with self.assertRaisesRegex(ValueError, "高德 URI 路线 action_link"):
            render_itinerary.validate_data(data)


if __name__ == "__main__":
    unittest.main()
