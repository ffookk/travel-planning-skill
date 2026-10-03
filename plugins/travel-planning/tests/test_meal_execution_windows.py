from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1] / "skills" / "travel-planning"
SPEC = importlib.util.spec_from_file_location("meal_execution_audit", SKILL / "scripts" / "audit_itinerary.py")
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class MealExecutionWindowsTest(unittest.TestCase):
    def example(self) -> dict:
        return json.loads((SKILL / "assets" / "example-itinerary.json").read_text(encoding="utf-8"))

    def test_public_example_passes_without_mutation(self) -> None:
        data = self.example()
        before = copy.deepcopy(data)
        result = audit.audit(data)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["restaurant_audit"]["used_meal_slot_count"], 3)
        self.assertEqual(data, before)

    def test_embedded_meal_outside_researched_window_blocks_despite_valid_parent_order(self) -> None:
        data = self.example()
        points = data["days"][1]["events"][0]["execution"]["checkpoints"]
        points[0]["end_time"] = "10:55"
        points[1].update(time="10:55", end_time="11:15")
        points[2]["time"] = "11:15"
        before = copy.deepcopy(data)
        result = audit.audit(data)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("meal_option.time_window" in message for message in result["blocking"]))
        self.assertEqual(data, before)

    def test_embedded_dated_meal_inherits_parent_zone_and_compares_actual_end(self) -> None:
        data = self.example()
        event = data["days"][1]["events"][0]
        event["timezone"] = "Asia/Shanghai"
        point = event["execution"]["checkpoints"][1]
        point.pop("time")
        point.pop("end_time")
        point.update(start_at="2026-10-18T10:35+08:00", end_at="2026-10-18T02:55Z", end_timezone="Etc/UTC")
        self.assertEqual(audit.audit(data)["status"], "pass")
        point["end_at"] = "2026-10-18T03:15Z"
        event["execution"]["checkpoints"][2]["time"] = "11:15"
        result = audit.audit(data)
        self.assertTrue(any("meal_option.time_window" in message for message in result["blocking"]))

    def test_standalone_dated_meal_cannot_extend_window_with_an_end_timezone(self) -> None:
        data = self.example()
        event = data["days"][0]["events"][3]
        event.update(start_at="2026-10-17T12:10+08:00", end_at="2026-10-17T13:10Z", timezone="Asia/Shanghai", end_timezone="Etc/UTC")
        result = audit.audit(data)
        self.assertTrue(any("meal_option.time_window" in message for message in result["blocking"]))
        event.update(end_at="2026-10-17T05:10Z", end_time="05:10")
        self.assertEqual(audit.audit(data)["status"], "pass")

    def test_fuzzy_researched_window_warns_without_using_restaurant_hours(self) -> None:
        data = self.example()
        meal = data["planning"]["meal_options"][2]
        meal["time_window"] = "around late morning"
        snapshots = {binding["snapshot_id"] for binding in meal["candidates"]}
        for snapshot in data["planning"]["restaurant_snapshots"]:
            if snapshot["snapshot_id"] in snapshots:
                snapshot["time_window"] = meal["time_window"]
                snapshot["operations"]["opening_hours"] = "00:00-23:59"
        result = audit.audit(data)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(any("time_window needs manual recheck" in message for message in result["warnings"]))

    def check(self, slot: dict, window: str, *, day: dict | None = None, parent: dict | None = None):
        return audit.meal_windows.check(slot, {"time_window": window}, day or {"date": "2026-10-18"}, {}, audit.render_itinerary.schedule_validation, parent)

    def test_boundaries_seconds_and_overnight_execution(self) -> None:
        for slot in (
            {"time": "10:35", "end_time": "10:55"},
            {"start_at": "2026-10-18T10:35+08:00", "end_at": "2026-10-18T10:55+08:00"},
        ):
            self.assertEqual(self.check(slot, "10:35-10:55"), (False, [], []))
        for end in ("2026-10-18T10:55:01+08:00", "2026-10-19T10:55+08:00"):
            self.assertTrue(self.check({"start_at": "2026-10-18T10:35+08:00", "end_at": end}, "10:35-10:55")[0])
        self.assertTrue(self.check({"time": "10:35"}, "10:35-10:55")[1])

    def test_unknown_endpoint_zone_does_not_assume_a_fixed_offset(self) -> None:
        slot = {"start_at": "2026-10-18T10:35+08:00", "end_at": "2026-10-18T02:55Z"}
        outside, errors, pending = self.check(slot, "10:35-10:55")
        self.assertFalse(outside)
        self.assertEqual(errors, [])
        self.assertTrue(any("IANA timezone" in message for message in pending))

    def test_checkpoint_on_another_date_does_not_reuse_parent_day_research(self) -> None:
        slot = {"start_at": "2026-10-19T10:35+08:00", "end_at": "2026-10-19T10:55+08:00"}
        self.assertTrue(self.check(slot, "10:35-10:55", parent={"timezone": "Asia/Shanghai"})[0])

    def test_iana_dst_contract_boundaries_require_an_unambiguous_window(self) -> None:
        day = {"date": "2026-11-01", "timezone": "America/New_York"}
        slot = {"start_at": "2026-11-01T01:30-04:00", "end_at": "2026-11-01T01:45-05:00"}
        self.assertEqual(self.check(slot, "00:00-03:00", day=day), (False, [], []))
        outside, errors, pending = self.check(slot, "01:00-02:00", day=day)
        self.assertFalse(outside)
        self.assertEqual(errors, [])
        self.assertTrue(any("ambiguous" in message for message in pending))
        slot = {"time": "02:30", "end_time": "03:30"}
        self.assertTrue(self.check(slot, "00:00-04:00", day={"date": "2026-03-08", "timezone": "America/New_York"})[1])


if __name__ == "__main__":
    unittest.main()
