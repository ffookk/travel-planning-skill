from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills" / "travel-planning" / "scripts" / "assemble_itinerary.py"
SPEC = importlib.util.spec_from_file_location("assemble_itinerary", MODULE_PATH)
assert SPEC and SPEC.loader
assemble_itinerary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assemble_itinerary)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class AssembleItineraryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name) / "trip"
        for name in ("results", "sources", "snapshots", "state", "artifacts"):
            (self.workspace / name).mkdir(parents=True, exist_ok=True)
        write_json(self.workspace / "selected-route.json", {"id": "route-1", "status": "confirmed"})
        research = {"schema_version": "travel-research-state/v2", "trip_id": "trip", "tasks": []}
        write_json(self.workspace / "state" / "research.json", research)
        digest = hashlib.sha256((self.workspace / "state" / "research.json").read_bytes()).hexdigest()
        write_json(self.workspace / "results" / "attractions.json", {
            "task_id": "attractions",
            "source_snapshot_ids": [],
            "entities": {
                "attractions": [{
                    "id": "museum", "name": "城市博物馆",
                    "official": {
                        "physical_address": "测试路1号", "homepage_url": "https://example.com/museum",
                        "notice_url": "https://example.com/museum/notices",
                    },
                    "operations": {"opening_hours": "09:00-17:00", "last_entry": "16:00"},
                    "entrance": {"name": "南门", "location_query": "城市博物馆南门"},
                    "exit": {"name": "东门", "location_query": "城市博物馆东门"},
                    "checkpoint_blueprint": [
                        {"id": "cp-a", "name": "入口"},
                        {"id": "cp-b", "name": "主展厅"},
                    ],
                    "reservation": {"required": False, "target_date": "2026-10-03"},
                    "cost_items": [{
                        "name": "基础票", "kind": "base_ticket", "pricing_role": "baseline",
                        "unit_price_cny": 0, "subtotal_cny": 0, "quantity": 2, "status": "free",
                    }],
                }]
            },
        })
        self.plan = {
            "schema_version": "itinerary-plan/v1",
            "research_state_sha256": digest,
            "trip": {
                "title": "测试行程", "date_range": "2026-10-03", "travelers": "2位成人",
                "updated_at": "2026-09-21",
            },
            "workflow": {"phase": "confirmed_planning", "selected_route_id": "route-1"},
            "collections": {
                "attractions": {
                    "task": "attractions", "path": "entities.attractions", "ids": ["museum"]
                }
            },
            "attraction_events": {
                "museum": {
                    "event_id": "event-museum", "start": "09:00", "end": "11:00",
                    "weather_id": "weather-1", "title": "城市博物馆",
                    "checkpoint_overrides": {"cp-b": {"required": False, "instruction": "时间不足可跳过"}},
                }
            },
            "days": [{
                "date": "2026-10-03",
                "events": [{"type": "attraction", "attraction_id": "museum"}],
            }],
        }
        self.plan_path = self.workspace / "state" / "itinerary-plan.json"
        write_json(self.plan_path, self.plan)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_assembles_selected_research_and_declarative_schedule(self) -> None:
        result = assemble_itinerary.assemble(self.workspace, self.plan_path)
        self.assertEqual(result["workflow"]["selected_route_id"], "route-1")
        self.assertEqual([item["id"] for item in result["planning"]["attractions"]], ["museum"])
        event = result["days"][0]["events"][0]
        self.assertEqual(event["id"], "event-museum")
        self.assertEqual(event["execution"]["entry"]["name"], "南门")
        self.assertFalse(event["execution"]["checkpoints"][1]["required"])
        self.assertEqual(event["execution"]["checkpoints"][1]["instruction"], "时间不足可跳过")
        self.assertNotIn("narration", event["execution"]["checkpoints"][0])
        self.assertNotIn("narration", event["execution"]["checkpoints"][1])
        self.assertEqual(result["planning"]["booking_tasks"][0]["event_id"], "event-museum")

    def test_keeps_researched_checkpoint_narration(self) -> None:
        task = json.loads((self.workspace / "results" / "attractions.json").read_text(encoding="utf-8"))
        task["entities"]["attractions"][0]["checkpoint_blueprint"][0]["narration"] = "观察主展厅入口保留的建筑构件。"
        write_json(self.workspace / "results" / "attractions.json", task)
        result = assemble_itinerary.assemble(self.workspace, self.plan_path)
        checkpoint = result["days"][0]["events"][0]["execution"]["checkpoints"][0]
        self.assertEqual(checkpoint["narration"], "观察主展厅入口保留的建筑构件。")

    def test_uses_verified_wechat_guide_for_booking_actions(self) -> None:
        task = json.loads((self.workspace / "results" / "attractions.json").read_text(encoding="utf-8"))
        attraction = task["entities"]["attractions"][0]
        attraction["reservation"] = {
            "required": True,
            "target_date": "2026-10-03",
            "action": "在微信公众号内预约",
        }
        attraction["official"]["wechat"] = {
            "account_name": "城市博物馆",
            "menu_path": "参观服务 → 预约",
            "guide_url": "https://mp.weixin.qq.com/s/museum-guide",
            "checked_at": "2026-09-22",
        }
        write_json(self.workspace / "results" / "attractions.json", task)
        result = assemble_itinerary.assemble(self.workspace, self.plan_path)
        event = result["days"][0]["events"][0]
        booking = result["planning"]["booking_tasks"][0]
        self.assertEqual(event["action_links"][0]["url"], "https://mp.weixin.qq.com/s/museum-guide")
        self.assertEqual(booking["action_links"][0]["type"], "official_wechat")
        self.assertEqual(booking["action_links"][0]["label"], "打开公众号预约说明")

    def test_rejects_plan_after_research_state_changes(self) -> None:
        write_json(self.workspace / "state" / "research.json", {
            "schema_version": "travel-research-state/v2", "trip_id": "trip", "tasks": ["changed"]
        })
        with self.assertRaisesRegex(assemble_itinerary.AssemblyError, "plan 已过期"):
            assemble_itinerary.assemble(self.workspace, self.plan_path)

    def test_rejects_missing_selected_entity(self) -> None:
        self.plan["collections"]["attractions"]["ids"] = ["missing"]
        write_json(self.plan_path, self.plan)
        with self.assertRaisesRegex(assemble_itinerary.AssemblyError, "缺少选定实体"):
            assemble_itinerary.assemble(self.workspace, self.plan_path)

    def test_deep_merge_replaces_lists_and_merges_objects(self) -> None:
        result = assemble_itinerary.deep_merge(
            {"nested": {"keep": 1, "replace": 2}, "items": [1, 2]},
            {"nested": {"replace": 3}, "items": [4]},
        )
        self.assertEqual(result, {"nested": {"keep": 1, "replace": 3}, "items": [4]})

    def assemble_lodging_price(self, lodging: dict) -> dict:
        source_path = self.workspace / "results" / "lodging.json"
        write_json(source_path, {
            "task_id": "lodging", "source_snapshot_ids": [],
            "entities": {"lodging_options": [{"id": "hotel", "name": "Synthetic hotel", **lodging}]},
        })
        self.plan["collections"]["lodging_options"] = {
            "task": "lodging", "path": "entities.lodging_options", "ids": ["hotel"],
        }
        write_json(self.plan_path, self.plan)
        source_before = source_path.read_bytes()
        plan_before = self.plan_path.read_bytes()
        result = assemble_itinerary.assemble(self.workspace, self.plan_path)
        self.assertEqual(source_path.read_bytes(), source_before)
        self.assertEqual(self.plan_path.read_bytes(), plan_before)
        return result["planning"]["lodging_options"][0]

    def test_lodging_uses_one_room_three_nights_without_rewriting_quote(self) -> None:
        lodging = {
            "room_requirement": {"rooms": 1}, "nights": 3,
            "quote": {"amount_per_room_per_night_cny": 199.99, "status": "verified", "source_ids": ["synthetic-quote"]},
        }
        original = deepcopy(lodging)
        result = self.assemble_lodging_price(lodging)
        self.assertEqual(result["price"], "快照约¥199.99/间夜；1间3晚规划估算约¥599.97（按每间夜单价计算，非供应商总价）")
        self.assertEqual(result["quote"], original["quote"])
        self.assertEqual(lodging, original)
        self.assertNotIn("requested_occupancy", result)
        self.assertNotIn("travelers", result["room_requirement"])

    def test_lodging_preserves_legacy_two_room_two_night_evidence(self) -> None:
        quote = {"amount_per_room_per_night_cny": 250, "two_rooms_two_nights_estimate_cny": 900}
        for quantities in ({}, {"room_requirement": {"rooms": 2}, "nights": 2}):
            with self.subTest(quantities=quantities):
                result = self.assemble_lodging_price({"quote": quote, **quantities})
                self.assertEqual(result["price"], "快照约¥250/间夜；2间2晚约¥900")
                self.assertEqual(result["quote"], quote)
        result = self.assemble_lodging_price({"quote": {"two_rooms_two_nights_estimate_cny": 900}})
        self.assertEqual(result["price"], "2间2晚约¥900")
        self.assertNotIn("nights", result)
        self.assertNotIn("room_requirement", result)

    def test_lodging_does_not_apply_legacy_total_to_another_stay(self) -> None:
        quote = {"amount_per_room_per_night_cny": 250, "two_rooms_two_nights_estimate_cny": 900}
        result = self.assemble_lodging_price({"quote": quote, "room_requirement": {"rooms": 1}, "nights": 3})
        self.assertIn("1间3晚规划估算约¥750", result["price"])
        self.assertNotIn("2间2晚", result["price"])
        self.assertNotIn("900", result["price"])
        self.assertEqual(result["quote"], quote)
        result = self.assemble_lodging_price({"quote": {"two_rooms_two_nights_estimate_cny": 900}, "nights": 3})
        self.assertEqual(result["price"], "待重新查询")

    def test_lodging_keeps_unit_price_when_quantities_are_unknown(self) -> None:
        for quantities in ({}, {"nights": 3}, {"room_requirement": {"rooms": 1}}, {"nights": None, "requested_occupancy": {"rooms": None}}):
            with self.subTest(quantities=quantities):
                result = self.assemble_lodging_price({"quote": {"amount_per_room_per_night_cny": 250}, **quantities})
                self.assertEqual(result["price"], "快照约¥250/间夜")
                self.assertNotIn("None", result["price"])
        self.assertEqual(self.assemble_lodging_price({})["price"], "待重新查询")

    def test_lodging_zero_quotes_are_not_missing(self) -> None:
        result = self.assemble_lodging_price({"quote": {"amount_per_room_per_night_cny": 0}, "requested_occupancy": {"rooms": 1}, "nights": 3})
        self.assertIn("快照约¥0/间夜；1间3晚规划估算约¥0", result["price"])
        result = self.assemble_lodging_price({"quote": {"amount_per_room_per_night_cny": 50, "two_rooms_two_nights_estimate_cny": 0}})
        self.assertEqual(result["price"], "快照约¥50/间夜；2间2晚约¥0")
        self.assertEqual(self.assemble_lodging_price({"price": 0})["price"], "0")
        self.assertEqual(self.assemble_lodging_price({"price": 0, "quote": {"display": "Other price"}})["price"], "0")

    def test_lodging_preserves_supplied_price_and_display(self) -> None:
        for supplied, expected in (
            ({"price": "Verified package: USD 120 including taxes"}, "Verified package: USD 120 including taxes"),
            ({"price": {"display": "¥3xx per room night", "amount": None}}, "¥3xx per room night"),
            ({"quote": {"display": "Provider total: ¥810 including taxes"}}, "Provider total: ¥810 including taxes"),
            ({"price": "Existing display", "quote": {"display": "Other display", "amount_per_room_per_night_cny": 250}}, "Existing display"),
        ):
            with self.subTest(supplied=supplied):
                result = self.assemble_lodging_price(supplied)
                self.assertEqual(result["price"], expected)
                if "quote" in supplied:
                    self.assertEqual(result["quote"], supplied["quote"])
        result = self.assemble_lodging_price({"price": "  ", "quote": {"amount_per_room_per_night_cny": "125.50"}, "nights": 3, "room_requirement": {"rooms": 1}})
        self.assertIn("¥125.5/间夜；1间3晚规划估算约¥376.5", result["price"])

    def test_lodging_rejects_invalid_amounts_even_with_supplied_display(self) -> None:
        for field in ("amount_per_room_per_night_cny", "two_rooms_two_nights_estimate_cny"):
            for value in (-1, True, float("nan"), float("inf"), "-1", "NaN", "Infinity", "unknown", [], {}):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(assemble_itinerary.AssemblyError, "finite nonnegative amount"):
                        self.assemble_lodging_price({"price": "Existing display", "quote": {field: value}})

    def test_lodging_rejects_invalid_counts_without_coercion(self) -> None:
        for value in (0, -1, True, 1.5, "2"):
            for quantities in ({"nights": value}, {"room_requirement": {"rooms": value}}, {"requested_occupancy": {"rooms": value}}):
                with self.subTest(quantities=quantities):
                    with self.assertRaisesRegex(assemble_itinerary.AssemblyError, "positive integer"):
                        self.assemble_lodging_price({"quote": {"amount_per_room_per_night_cny": 250}, **quantities})
        with self.assertRaisesRegex(assemble_itinerary.AssemblyError, "room counts must agree"):
            self.assemble_lodging_price({"room_requirement": {"rooms": 1}, "requested_occupancy": {"rooms": 2}})

    def test_lodging_rejects_extreme_decimal_exponents_before_arithmetic(self) -> None:
        for amount in ("1e999999", "1e-1000100"):
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(assemble_itinerary.AssemblyError, "1000 integer and fractional digits"):
                    self.assemble_lodging_price({"quote": {"amount_per_room_per_night_cny": amount}, "room_requirement": {"rooms": 10}, "nights": 1})
        result = self.assemble_lodging_price({"quote": {"amount_per_room_per_night_cny": "-0e-1000100"}, "room_requirement": {"rooms": 1}, "nights": 3})
        self.assertIn("快照约¥0/间夜；1间3晚规划估算约¥0", result["price"])

    def test_lodging_derives_nights_from_explicit_calendar_dates(self) -> None:
        lodging = {
            "quote": {"amount_per_room_per_night_cny": 100}, "requested_occupancy": {"rooms": 1},
            "check_in_date": "2028-02-28", "check_out_date": "2028-03-02",
        }
        result = self.assemble_lodging_price(lodging)
        self.assertIn("1间3晚规划估算约¥300", result["price"])
        self.assertEqual(result["check_in_date"], lodging["check_in_date"])
        self.assertEqual(result["check_out_date"], lodging["check_out_date"])
        self.assertNotIn("nights", result)
        lodging["nights"] = 3
        self.assertEqual(self.assemble_lodging_price(lodging)["price"], result["price"])

    def test_lodging_rejects_invalid_or_conflicting_date_spans(self) -> None:
        for dates in (
            {"check_in_date": "2026-10-03", "check_out_date": "2026-10-03"},
            {"check_in_date": "2026-10-04", "check_out_date": "2026-10-03"},
            {"check_in_date": "2026-10-03", "check_out_date": "2026-10-06", "nights": 2},
            {"check_in_date": "2026-10-03T15:00:00", "check_out_date": "2026-10-06"},
            {"check_in_date": "invalid", "check_out_date": "2026-10-06"},
        ):
            with self.subTest(dates=dates):
                with self.assertRaises(assemble_itinerary.AssemblyError):
                    self.assemble_lodging_price(dates)


if __name__ == "__main__":
    unittest.main()
