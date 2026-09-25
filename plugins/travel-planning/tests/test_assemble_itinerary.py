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

    def assemble_lodging(self, item: dict) -> dict:
        task_path = self.workspace / "results" / "stay-food.json"
        write_json(task_path, {
            "task_id": "stay-food",
            "source_snapshot_ids": [],
            "entities": {"lodging_options": [item]},
        })
        self.plan["collections"]["lodging_options"] = {
            "task": "stay-food", "path": "entities.lodging_options", "ids": [item["id"]],
        }
        self.plan["days"][0]["events"].append({
            "id": "event-hotel", "type": "lodging", "lodging_id": item["id"],
            "title": "Example Hotel", "time": "18:00",
        })
        write_json(self.plan_path, self.plan)
        original_task = task_path.read_bytes()
        original_plan = self.plan_path.read_bytes()

        result = assemble_itinerary.assemble(self.workspace, self.plan_path)

        self.assertEqual(task_path.read_bytes(), original_task)
        self.assertEqual(self.plan_path.read_bytes(), original_plan)
        lodging = result["planning"]["lodging_options"][0]
        self.assertEqual(result["days"][0]["events"][-1]["lodging_id"], lodging["id"])
        return lodging

    def test_missing_lodging_verification_remains_to_recheck(self) -> None:
        lodging = self.assemble_lodging({"id": "hotel-1", "name": "Example Hotel"})

        self.assertEqual(lodging["location_verification"], {"status": "to_recheck"})

    def test_lodging_poi_timestamp_does_not_establish_identity_verification(self) -> None:
        location = {
            "physical_address": "1 Example Street",
            "coordinates": "120.0,30.0",
            "poi_verified_at": "2026-09-18",
        }
        lodging = self.assemble_lodging({
            "id": "hotel-1", "name": "Example Hotel", "location": location,
            "source_ids": ["map-source"],
        })

        self.assertEqual(lodging["location_verification"], {"status": "to_recheck"})
        self.assertEqual(lodging["location"], location)
        self.assertEqual(lodging["source_ids"], ["map-source"])

    def test_keeps_pending_lodging_verification_and_its_evidence(self) -> None:
        verification = {
            "status": "to_recheck", "checked_at": "2026-09-19",
            "method": "Address comparison", "source_ids": ["hotel-source"],
            "reason": "The property name matches but its district is unresolved.",
        }
        lodging = self.assemble_lodging({
            "id": "hotel-1", "name": "Example Hotel",
            "location": {"poi_verified_at": "2026-09-20"},
            "location_verification": verification,
        })

        self.assertEqual(lodging["location_verification"], verification)

    def test_keeps_verified_lodging_conclusion_without_replacing_evidence(self) -> None:
        verification = {
            "status": "verified", "checked_at": "2026-09-17",
            "method": "Compared full name, city, district, address and coordinates",
            "source_ids": ["official-hotel", "map-source"],
        }
        lodging = self.assemble_lodging({
            "id": "hotel-1", "name": "Example Hotel",
            "location": {"poi_verified_at": "2026-09-20"},
            "source_ids": ["quote-source"],
            "location_verification": verification,
        })

        self.assertEqual(lodging["location_verification"], verification)

    def test_normalizing_lodging_preserves_input_and_does_not_share_evidence(self) -> None:
        item = {
            "id": "hotel-1", "name": "Example Hotel",
            "location_verification": {
                "source_ids": ["map-source"],
                "checked_at": "2026-09-19",
                "evidence": {"address_match": False},
            },
        }
        original = deepcopy(item)

        lodging = assemble_itinerary.normalize_lodging(
            item, assemble_itinerary.default_settings(self.plan),
        )

        self.assertEqual(lodging["location_verification"], {
            **original["location_verification"], "status": "to_recheck",
        })
        self.assertEqual(item, original)
        lodging["location_verification"]["source_ids"].append("another-source")
        lodging["location_verification"]["evidence"]["address_match"] = True
        self.assertEqual(item, original)

    def test_deep_merge_replaces_lists_and_merges_objects(self) -> None:
        result = assemble_itinerary.deep_merge(
            {"nested": {"keep": 1, "replace": 2}, "items": [1, 2]},
            {"nested": {"replace": 3}, "items": [4]},
        )
        self.assertEqual(result, {"nested": {"keep": 1, "replace": 3}, "items": [4]})


if __name__ == "__main__":
    unittest.main()
