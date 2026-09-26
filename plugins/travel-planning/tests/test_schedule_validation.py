from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "travel-planning"
SPEC = importlib.util.spec_from_file_location("schedule_audit", SKILL_ROOT / "scripts" / "audit_itinerary.py")
assert SPEC and SPEC.loader
audit_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_module)
renderer = audit_module.render_itinerary


def itinerary(events: list[dict], **trip_fields: object) -> dict:
    return {
        "trip": {"title": "Synthetic timed itinerary", **trip_fields},
        "days": [{"date": "2026-10-17", "events": events}],
    }


def dated_event(start: str, end: str, **fields: object) -> dict:
    return {"id": "event-1", "title": "Synthetic journey", "type": "transport", "start_at": start, "end_at": end, **fields}


class ScheduleValidationTest(unittest.TestCase):
    def example(self) -> dict:
        return json.loads((SKILL_ROOT / "assets" / "example-itinerary.json").read_text(encoding="utf-8"))

    def messages(self, data: dict, kind: str = "blocking") -> str:
        return "\n".join(audit_module.audit(data)[kind])

    def test_legacy_example_and_overlap_checks_remain_supported(self) -> None:
        data = self.example()
        self.assertEqual(audit_module.audit(data)["status"], "pass")
        data["days"][0]["events"][2]["time"] = "10:00"
        self.assertIn("时间重叠", self.messages(data))

    def test_overnight_dated_journey_passes_and_displays_both_dates(self) -> None:
        data = itinerary([dated_event("2026-10-17T23:30:00+08:00", "2026-10-18T00:30:00+08:00", timezone="Asia/Shanghai")])
        before = copy.deepcopy(data)
        self.assertEqual(audit_module.audit(data)["blocking"], [])
        document = renderer.build(data)
        self.assertIn("2026-10-17 23:30:00+08:00", document)
        self.assertIn("2026-10-18 00:30:00+08:00", document)
        self.assertEqual(data, before)

    def test_international_local_arrival_can_be_earlier_than_departure(self) -> None:
        data = itinerary([dated_event("2026-10-17T12:00:00+11:00", "2026-10-17T06:00:00-07:00", timezone="Australia/Sydney", end_timezone="America/Los_Angeles")])
        self.assertEqual(audit_module.audit(data)["blocking"], [])
        data["days"].append({"date": "2026-10-17", "events": [dated_event("2026-10-17T05:30:00-07:00", "2026-10-17T06:30:00-07:00", id="event-2")]})
        self.assertIn("actual event times overlap", self.messages(data))

    def test_aware_chronology_is_compared_across_day_boundaries(self) -> None:
        data = itinerary([dated_event("2026-10-17T23:30+08:00", "2026-10-18T02:00+08:00")])
        data["days"].append({"date": "2026-10-18", "events": [dated_event("2026-10-18T01:00+08:00", "2026-10-18T02:30+08:00", id="event-2")]})
        self.assertIn("actual event times overlap", self.messages(data))

    def test_missing_offsets_pairs_and_conflicting_display_times_are_rejected(self) -> None:
        for event in (
            dated_event("2026-10-17T10:00", "2026-10-17T11:00"),
            {"id": "missing-end", "type": "rest", "start_at": "2026-10-17T10:00+08:00"},
            dated_event("2026-10-17T10:00+08:00", "2026-10-17T09:00+08:00"),
            dated_event("2026-10-17T10:00+08:00", "2026-10-17T11:00+08:00", time="09:00"),
        ):
            with self.subTest(event=event):
                data = itinerary([event])
                self.assertEqual(audit_module.audit(data)["status"], "fail")
                with self.assertRaises(ValueError):
                    renderer.build(data)

    def test_iana_legacy_times_reject_dst_gap_and_fold_without_offsets(self) -> None:
        for day_date, reason in (("2026-03-08", "nonexistent"), ("2026-11-01", "ambiguous")):
            hour = "02:30" if reason == "nonexistent" else "01:30"
            data = itinerary([{"type": "rest", "title": "DST case", "time": hour, "end_time": "03:30"}], timezone="America/New_York")
            data["days"][0]["date"] = day_date
            self.assertIn(reason, self.messages(data))

    def test_explicit_offsets_disambiguate_fold_and_use_elapsed_duration(self) -> None:
        data = itinerary([dated_event("2026-11-01T01:30:00-04:00", "2026-11-01T01:30:00-05:00", timezone="America/New_York", route_id="route")])
        data["days"][0]["date"] = "2026-11-01"
        data["planning"] = {"transport_edges": [{"id": "route", "door_to_door_minutes": 60}]}
        self.assertEqual(audit_module.audit(data)["blocking"], [])
        data["planning"]["transport_edges"][0]["door_to_door_minutes"] = 61
        self.assertIn("shorter than door_to_door_minutes", self.messages(data))

    def test_explicit_nonexistent_time_and_wrong_iana_offset_are_rejected(self) -> None:
        for start in ("2026-03-08T02:30:00-05:00", "2026-03-08T01:30:00-04:00"):
            data = itinerary([dated_event(start, "2026-03-08T04:30:00-04:00", timezone="America/New_York")])
            data["days"][0]["date"] = "2026-03-08"
            self.assertIn("does not match", self.messages(data))

    def test_unambiguous_iana_times_resolve_and_unknown_boundary_warns(self) -> None:
        data = itinerary([{"id": "local", "type": "rest", "time": "09:00", "end_time": "10:00"}], timezone="Asia/Shanghai")
        self.assertEqual(audit_module.audit(data)["blocking"], [])
        del data["trip"]["timezone"]
        data["days"][0]["events"].append(dated_event("2026-10-17T10:00+08:00", "2026-10-17T11:00+08:00"))
        self.assertIn("timezone-free events", self.messages(data, "warnings"))

    def test_overnight_attraction_accepts_explicit_checkpoint_instants(self) -> None:
        event = dated_event("2026-10-17T23:00+08:00", "2026-10-18T01:00+08:00", type="attraction", timezone="Asia/Shanghai")
        event["execution"] = {"checkpoints": [
            {"order": 1, "name": "Entry", "start_at": "2026-10-17T23:00+08:00", "end_at": "2026-10-18T00:00+08:00"},
            {"order": 2, "name": "Exit", "start_at": "2026-10-18T00:00+08:00", "end_at": "2026-10-18T01:00+08:00"},
        ]}
        data = itinerary([event])
        self.assertEqual(audit_module.audit(data)["blocking"], [])
        event["execution"]["checkpoints"][1]["start_at"] = "2026-10-17T23:30+08:00"
        self.assertIn("checkpoint actual times overlap", self.messages(data))

    def test_exact_transport_duration_blocks_impossible_slot(self) -> None:
        for duration in ({"door_to_door_minutes": 120}, {"door_to_door_duration": "120 分钟"}, {"door_to_door_duration": "120 minutes"}):
            data = self.example()
            data["days"][0]["events"][0]["end_time"] = "08:41"
            data["planning"]["transport_edges"][0].update(duration)
            self.assertIn("shorter than door_to_door_minutes", self.messages(data))

    def test_uncertain_transport_text_warns_without_inventing_minutes(self) -> None:
        data = self.example()
        data["planning"]["transport_edges"][0]["door_to_door_duration"] = "about 30-90 minutes including queues"
        self.assertEqual(audit_module.audit(data)["status"], "pass")
        self.assertIn("not an exact minute value", self.messages(data, "warnings"))

    def test_invalid_structured_minutes_are_not_silently_ignored(self) -> None:
        for value in (-1, True, "120", float("inf"), 10 ** 400):
            data = self.example()
            data["planning"]["transport_edges"][0]["door_to_door_minutes"] = value
            self.assertIn("finite nonnegative number", self.messages(data))

    def test_arrival_after_last_entry_and_visit_outside_opening_block(self) -> None:
        data = self.example()
        event = data["days"][0]["events"][1]
        event["admission"].update(last_entry="08:00", opening_hours="07:00-09:00")
        self.assertIn("after last_entry", self.messages(data))
        self.assertIn("outside opening_hours", self.messages(data))

    def test_dated_opening_windows_and_cutoff_compare_actual_instants(self) -> None:
        event = dated_event("2026-10-17T09:00+08:00", "2026-10-17T10:00+08:00", type="attraction")
        event["execution"] = {"checkpoints": [{"order": 1, "name": "Visit", "time": "09:00", "end_time": "10:00"}]}
        event["admission"] = {
            "last_entry_at": "2026-10-17T01:00Z",
            "opening_windows": [{"start_at": "2026-10-17T00:00Z", "end_at": "2026-10-17T02:00Z"}],
        }
        data = itinerary([event])
        self.assertEqual(audit_module.audit(data)["blocking"], [])
        event["admission"]["last_entry_at"] = "2026-10-17T00:59Z"
        self.assertIn("after last_entry_at", self.messages(data))
        event["admission"]["opening_windows"][0]["end_at"] = "2026-10-17T01:59Z"
        self.assertIn("outside opening_windows", self.messages(data))

    def test_confirmed_attraction_can_use_dated_checkpoints_without_clock_fields(self) -> None:
        data = self.example()
        data["trip"]["timezone"] = "Asia/Shanghai"
        event = data["days"][0]["events"][1]
        event["start_at"] = f'2026-10-17T{event["time"]}:00+08:00'
        event["end_at"] = f'2026-10-17T{event["end_time"]}:00+08:00'
        for point in event["execution"]["checkpoints"]:
            point["start_at"] = f'2026-10-17T{point.pop("time")}:00+08:00'
            point["end_at"] = f'2026-10-17T{point.pop("end_time")}:00+08:00'
        before = copy.deepcopy(data)
        self.assertEqual(audit_module.audit(data)["blocking"], [])
        self.assertIn("2026-10-17 09:00:00+08:00", renderer.build(data))
        self.assertEqual(data, before)

    def test_admission_timezone_controls_local_cutoff_comparison(self) -> None:
        event = dated_event("2026-10-17T01:00Z", "2026-10-17T02:00Z", type="attraction")
        event["execution"] = {"checkpoints": [{"order": 1, "name": "Visit", "time": "01:00", "end_time": "02:00"}]}
        event["admission"] = {"timezone": "Asia/Shanghai", "last_entry": "08:00"}
        self.assertIn("after last_entry", self.messages(itinerary([event])))

    def test_opening_hours_normalize_both_endpoints_to_known_venue_zone(self) -> None:
        for scope in ("admission", "event", "day", "trip"):
            event = dated_event("2026-10-17T09:00+08:00", "2026-10-17T12:00Z", type="attraction", end_timezone="Etc/UTC")
            event["admission"] = {"opening_hours": "08:00-18:00"}
            data = itinerary([event])
            target = {"admission": event["admission"], "event": event, "day": data["days"][0], "trip": data["trip"]}[scope]
            target["timezone"] = "Asia/Shanghai"
            with self.subTest(scope=scope):
                self.assertIn("outside opening_hours", self.messages(data))

    def test_differing_offsets_without_venue_zone_require_opening_recheck(self) -> None:
        event = dated_event("2026-10-17T09:00+08:00", "2026-10-17T12:00Z", type="attraction")
        event["admission"] = {"opening_hours": "08:00-18:00"}
        data = itinerary([event])
        self.assertIn("IANA venue timezone or dated opening_windows", self.messages(data, "warnings"))
        event["admission"]["opening_windows"] = [{"start_at": "2026-10-17T08:00+08:00", "end_at": "2026-10-17T18:00+08:00"}]
        self.assertIn("outside opening_windows", self.messages(data))
        self.assertNotIn("IANA venue timezone", self.messages(data, "warnings"))

    def test_opening_hours_use_iana_dst_rules_for_both_endpoint_offsets(self) -> None:
        event = dated_event("2026-11-01T01:30-04:00", "2026-11-01T02:30-05:00", type="attraction", timezone="America/New_York")
        event["admission"] = {"opening_hours": "01:00-03:00"}
        start, end = renderer.schedule_validation.window(event, {"date": "2026-11-01"}, {})
        errors, pending = renderer.schedule_validation.feasibility(event, {}, start, end)
        self.assertEqual((errors, pending), ([], []))
        event["admission"]["opening_hours"] = "01:00-02:00"
        errors, _ = renderer.schedule_validation.feasibility(event, {}, start, end)
        self.assertIn("Attraction visit is outside opening_hours", errors)

    def test_unbounded_numeric_duration_text_is_rejected_as_validation_error(self) -> None:
        data = self.example()
        data["planning"]["transport_edges"][0]["door_to_door_duration"] = "9" * 400 + " minutes"
        self.assertIn("finite minute value", self.messages(data))

    def test_ambiguous_opening_text_warns_and_meal_checks_are_preserved(self) -> None:
        data = self.example()
        data["days"][0]["events"][1]["admission"].update(last_entry="30 minutes before closing", opening_hours="seasonal hours; see notice")
        self.assertIn("Last entry needs manual recheck", self.messages(data, "warnings"))
        self.assertIn("Opening hours need manual recheck", self.messages(data, "warnings"))
        meal = data["days"][0]["events"][3]
        meal.update(time="13:20", end_time="14:20")
        self.assertIn("超出 meal_option.time_window", self.messages(data))


if __name__ == "__main__":
    unittest.main()
