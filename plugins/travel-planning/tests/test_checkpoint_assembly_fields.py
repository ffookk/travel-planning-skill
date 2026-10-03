from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1] / "skills" / "travel-planning"


def load(name: str):
    spec = importlib.util.spec_from_file_location("checkpoint_fields_" + name, SKILL / "scripts" / (name + ".py"))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


assembler = load("assemble_itinerary")
audit = load("audit_itinerary")


class CheckpointAssemblyFieldsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.example = json.loads((SKILL / "assets" / "example-itinerary.json").read_text(encoding="utf-8"))
        self.attraction = copy.deepcopy(self.example["planning"]["attractions"][1])
        self.point = copy.deepcopy(self.example["days"][1]["events"][0]["execution"]["checkpoints"][1])
        self.point.update(
            images=[{"url": "https://example.com/tea.jpg", "alt": "Synthetic tea stop", "source_url": "https://example.com/tea", "license": "CC0", "author": "Synthetic photographer"}],
            action_links=[{"type": "official", "label": "Synthetic stop details", "url": "https://example.com/tea", "provider": "Synthetic venue", "checked_at": "2026-09-20", "disclaimer": "Check before departure"}],
            fallback="Synthetic rain alternative",
            private_research_note="Do not copy arbitrary research fields",
        )
        self.attraction["checkpoint_blueprint"] = [self.point]
        self.config = {"event_id": "synthetic-event", "title": self.attraction["name"], "start": "10:35", "end": "10:55", "weather_id": "w2"}
        self.defaults = assembler.default_settings({"trip": self.example["trip"]})

    def build(self) -> dict:
        return assembler.build_attraction_event(self.attraction, self.config, self.defaults)

    def test_public_assembly_path_retains_supported_checkpoint_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "state").mkdir()
            (root / "results").mkdir()
            research = b'{"schema_version":"travel-research-state/v2","tasks":[]}'
            (root / "state" / "research.json").write_bytes(research)
            (root / "selected-route.json").write_text('{"id":"synthetic-route"}', encoding="utf-8")
            source = root / "results" / "attractions.json"
            source.write_text(json.dumps({"entities": {"attractions": [self.attraction]}}), encoding="utf-8")
            plan = {
                "schema_version": "itinerary-plan/v1", "research_state_sha256": hashlib.sha256(research).hexdigest(),
                "trip": self.example["trip"], "workflow": {"phase": "confirmed_planning", "selected_route_id": "synthetic-route"},
                "collections": {"attractions": {"task": "attractions", "path": "entities.attractions"}},
                "attraction_events": {self.attraction["id"]: self.config},
                "days": [{"date": "2026-10-18", "events": [{"type": "attraction", "attraction_id": self.attraction["id"]}]}],
            }
            plan_path = root / "state" / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            before = source.read_bytes(), plan_path.read_bytes()
            result = assembler.assemble(root, plan_path)
            point = result["days"][0]["events"][0]["execution"]["checkpoints"][0]
            for field in ("meal_id", "images", "action_links", "fallback"):
                self.assertEqual(point[field], self.point[field])
            self.assertNotIn("private_research_note", point)
            self.assertEqual((source.read_bytes(), plan_path.read_bytes()), before)

    def test_overrides_win_and_preserved_nested_values_are_independent(self) -> None:
        override = {"meal_id": "replacement-meal", "images": [], "action_links": [], "fallback": "Replacement fallback"}
        self.config["checkpoint_overrides"] = {self.point["id"]: override}
        before = copy.deepcopy((self.attraction, self.config))
        point = self.build()["execution"]["checkpoints"][0]
        for field, value in override.items():
            self.assertEqual(point[field], value)
        point["images"].append({"alt": "Changed output only"})
        self.assertEqual((self.attraction, self.config), before)
        del self.config["checkpoint_overrides"]
        point = self.build()["execution"]["checkpoints"][0]
        point["images"][0]["alt"] = "Changed output only"
        self.assertEqual(self.point["images"][0]["alt"], "Synthetic tea stop")

    def test_generated_identity_order_and_times_still_control_the_schedule(self) -> None:
        self.config["checkpoint_overrides"] = {self.point["id"]: {"id": "override-id", "order": 99, "time": "01:00", "end_time": "02:00"}}
        point = self.build()["execution"]["checkpoints"][0]
        self.assertEqual((point["id"], point["order"], point["time"], point["end_time"]), (f'cp-{self.attraction["id"]}-1', 1, "10:35", "10:55"))
        for field in ("meal_id", "images", "action_links", "fallback"):
            self.point.pop(field)
        point = self.build()["execution"]["checkpoints"][0]
        self.assertTrue(all(field not in point for field in ("meal_id", "images", "action_links", "fallback")))

    def test_preserved_content_reaches_existing_renderer_and_image_gate(self) -> None:
        before = copy.deepcopy(self.example)
        self.assertEqual(audit.audit(self.example)["status"], "pass")
        self.assertEqual(self.example, before)
        event = self.example["days"][1]["events"][0]
        point = self.build()["execution"]["checkpoints"][0]
        point["id"], point["order"] = event["execution"]["checkpoints"][1]["id"], 2
        event["execution"]["checkpoints"][1] = point
        self.assertEqual(audit.audit(self.example)["status"], "pass")
        html = audit.render_itinerary.build(self.example)
        selected = self.example["planning"]["meal_options"][2]["selected_candidate_id"]
        restaurant = next(item for item in self.example["planning"]["restaurants"] if item["id"] == selected)
        for value in ("Synthetic tea stop", "Synthetic stop details", "Synthetic rain alternative", restaurant["name"]):
            self.assertTrue(value in html, f"Missing rendered checkpoint content: {value}")
        del point["images"][0]["license"]
        self.assertEqual(audit.audit(self.example)["status"], "fail")


if __name__ == "__main__":
    unittest.main()
