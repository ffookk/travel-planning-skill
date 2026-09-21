from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "travel-planning"
MODULE_PATH = SKILL_ROOT / "scripts" / "audit_itinerary.py"
SPEC = importlib.util.spec_from_file_location("audit_itinerary", MODULE_PATH)
assert SPEC and SPEC.loader
audit_itinerary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_itinerary)


def add_expired_inventory(data: dict) -> str:
    snapshot_id = "0123456789abcdef01234567"
    data["planning"]["source_snapshots"] = [{
        "schema_version": "travel-source-snapshot/v1", "snapshot_id": snapshot_id,
        "snapshot_kind": "quote", "status": "platform_reported",
        "provider": {"id": "fliggy_flyai", "name": "飞猪 FlyAI"},
        "product_type": "flight", "tool": "search-flight", "query": {},
        "freshness": {"checked_at": "2000-01-01T10:00:00+08:00", "expires_at": "2000-01-01T10:30:00+08:00", "dynamic": True},
        "items": [{"offer_id": "mu1", "name": "MU1", "price": {"display": "¥500"}, "availability": {}, "action_link": None}],
        "count": 1, "raw_response_hash": "sha256:" + "a" * 64,
        "source": {"title": "飞猪", "url": "https://example.com", "kind": "official_platform_api"}, "disclaimer": "复核",
    }]
    route = next(item for item in data["planning"]["transport_edges"] if item["id"] == "r1")
    route["inventory_refs"] = [{"snapshot_id": snapshot_id, "offer_id": "mu1", "role": "candidate_quote"}]
    return snapshot_id


class AuditItineraryTest(unittest.TestCase):
    def load_example(self) -> dict:
        return json.loads((SKILL_ROOT / "assets" / "example-itinerary.json").read_text(encoding="utf-8"))

    def test_example_passes(self) -> None:
        result = audit_itinerary.audit(self.load_example())
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["blocking"], [])
        self.assertEqual(result["restaurant_audit"]["used_meal_slot_count"], 3)
        self.assertEqual(result["restaurant_audit"]["restaurant_count"], 5)

    def test_detects_time_overlap(self) -> None:
        data = self.load_example()
        data["days"][0]["events"][2]["time"] = "10:00"
        result = audit_itinerary.audit(data)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("时间重叠" in item for item in result["blocking"]))

    def test_detects_missing_meal_in_active_window(self) -> None:
        data = self.load_example()
        data["days"][0]["events"] = [event for event in data["days"][0]["events"] if event["type"] != "meal"]
        data["days"][0]["events"][-1]["end_time"] = "13:00"
        result = audit_itinerary.audit(data)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("午餐窗口" in item for item in result["blocking"]))

    def test_meal_exemption_is_explicit(self) -> None:
        data = self.load_example()
        data["days"][0]["events"] = [event for event in data["days"][0]["events"] if event["type"] != "meal"]
        data["days"][0]["events"][-1]["end_time"] = "13:00"
        data["days"][0]["meal_exemptions"] = {"午餐": "12:00 前结束正式活动，用户自行安排"}
        result = audit_itinerary.audit(data)
        self.assertFalse(any("午餐窗口" in item for item in result["blocking"]))

    def test_detects_internal_checkpoint_overlap(self) -> None:
        data = self.load_example()
        data["days"][0]["events"][1]["execution"]["checkpoints"][1]["time"] = "09:20"
        result = audit_itinerary.audit(data)
        self.assertTrue(any("节点时间重叠" in item for item in result["blocking"]))

    def test_detects_meal_event_outside_researched_time_window(self) -> None:
        data = self.load_example()
        meal_event = data["days"][0]["events"][3]
        meal_event["time"] = "13:20"
        meal_event["end_time"] = "14:20"
        result = audit_itinerary.audit(data)
        self.assertTrue(any("超出 meal_option.time_window" in item for item in result["blocking"]))

    def test_warns_about_unbound_meal_research(self) -> None:
        data = self.load_example()
        data["planning"]["meal_options"].append({"id": "unused-meal"})
        result = audit_itinerary.audit(data)
        self.assertTrue(any("未绑定" in item and "unused-meal" in item for item in result["warnings"]))

    def test_confirmed_plan_warns_when_selected_inventory_snapshot_expired(self) -> None:
        data = self.load_example()
        snapshot_id = add_expired_inventory(data)
        result = audit_itinerary.audit(data)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(any(snapshot_id in item and "已过期" in item for item in result["warnings"]))
        self.assertEqual(result["inventory_audit"]["selected_reference_count"], 1)

    def test_final_plan_blocks_selected_transport_without_multi_sort_coverage(self) -> None:
        data = self.load_example()
        snapshot_id = add_expired_inventory(data)
        snapshot = next(
            item for item in data["planning"]["source_snapshots"]
            if item["snapshot_id"] == snapshot_id
        )
        snapshot["freshness"] = {
            "checked_at": "2099-01-01T10:00:00+08:00",
            "expires_at": "2099-01-01T10:30:00+08:00",
            "dynamic": True,
        }
        data["workflow"]["phase"] = "final"
        result = audit_itinerary.audit(data)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("排序覆盖" in item for item in result["blocking"]))
        self.assertTrue(result["inventory_audit"]["transport_coverage_gaps"])


if __name__ == "__main__":
    unittest.main()
