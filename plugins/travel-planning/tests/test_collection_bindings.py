from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "travel-planning" / "scripts" / "assemble_itinerary.py"
SPEC = importlib.util.spec_from_file_location("collection_binding_assembler", SCRIPT)
assembler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(assembler)


class CollectionBindingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        for folder in ("state", "results", "sources", "snapshots"):
            (self.workspace / folder).mkdir()
        self.write(self.workspace / "selected-route.json", {"id": "synthetic-route"})
        self.write(self.workspace / "state" / "research.json", {"schema_version": "travel-research-state/v2", "tasks": []})
        self.records = [
            {"id": value, "code": "code-" + value, "summary": "Synthetic weather " + value,
             "extension": {"keep": "original", "replace": "original"}, "action_links": []}
            for value in ("a", "b", "ab")
        ]
        self.payload = {"task_id": "synthetic", "source_snapshot_ids": [], "entities": {"weather": self.records}}
        self.source = self.workspace / "results" / "synthetic.json"
        self.file_source = self.workspace / "state" / "weather.json"
        self.write(self.source, self.payload)
        self.write(self.file_source, self.payload)
        self.binding = {"task": "synthetic", "path": "entities.weather"}
        self.plan = {
            "schema_version": "itinerary-plan/v1",
            "research_state_sha256": hashlib.sha256((self.workspace / "state" / "research.json").read_bytes()).hexdigest(),
            "trip": {"title": "Synthetic trip", "date_range": "2028-01-01", "travelers": "2 adults", "updated_at": "2028-01-01"},
            "workflow": {"phase": "confirmed_planning", "selected_route_id": "synthetic-route"},
            "collections": {"weather": self.binding},
            "days": [{"date": "2028-01-01", "events": [{"id": "rest", "type": "rest", "title": "Rest", "time": "09:00"}]}],
        }
        self.plan_path = self.workspace / "state" / "itinerary-plan.json"

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def assemble(self):
        self.write(self.plan_path, self.plan)
        return assembler.assemble(self.workspace, self.plan_path)

    def reject_before_read(self, bindings):
        with patch.object(assembler, "read_json") as read:
            with self.assertRaises(assembler.AssemblyError) as caught:
                assembler.load_collections(self.workspace, {"collections": bindings})
            read.assert_not_called()
        self.assertNotIn("SYNTHETIC-PRIVATE", str(caught.exception))
        self.assertNotIn(str(self.workspace), str(caught.exception))

    def test_scalar_ids_cannot_silently_select_individual_characters(self):
        self.reject_before_read({"weather": {**self.binding, "ids": "ab"}})
        self.binding["ids"] = ["ab"]
        result = self.assemble()
        self.assertEqual([item["id"] for item in result["planning"]["weather"]], ["ab"])

    def test_duplicate_and_nonstring_ids_fail_before_reads(self):
        for values in (["a", "a"], ["SYNTHETIC-PRIVATE", "SYNTHETIC-PRIVATE"], [1], [False], [None], [""], {}, None, 1):
            with self.subTest(values=values):
                self.reject_before_read({"weather": {**self.binding, "ids": values}})

    def test_exactly_one_source_is_required_without_silent_precedence(self):
        for binding in (
            {"task": "synthetic", "file": "state/weather.json", "path": "entities.weather"},
            {"task": "synthetic", "file": None, "path": "entities.weather"},
            {"path": "entities.weather"},
        ):
            with self.subTest(binding=binding):
                self.reject_before_read({"weather": binding})

    def test_binding_field_types_match_the_declared_contract(self):
        invalid = [None, [], "SYNTHETIC-PRIVATE", {"task": "synthetic"}]
        invalid.extend({**self.binding, key: value} for key, values in (
            ("task", [None, False, 1, "", []]), ("path", [None, 1, [], {}]),
            ("id_key", [None, 1, "", []]), ("patches", [None, [], {"a": None}, {"a": []}]),
            ("append", [None, {}, "", [None], ["SYNTHETIC-PRIVATE"]]),
        ) for value in values)
        invalid.extend({"file": value, "path": "entities.weather"} for value in (None, False, "", []))
        for binding in invalid:
            with self.subTest(binding=binding):
                self.reject_before_read({"weather": binding})
        for bindings in (None, [], "", 1):
            with self.subTest(bindings=bindings):
                self.reject_before_read(bindings)

    def test_all_bindings_are_validated_before_the_first_collection_read(self):
        bindings = {"weather": self.binding, "extension_collection": {**self.binding, "ids": "SYNTHETIC-PRIVATE"}}
        self.reject_before_read(bindings)

    def test_omitted_empty_and_ordered_selections_have_distinct_meanings(self):
        for values, expected in ((None, ["a", "b", "ab"]), ([], []), (["b", "a"], ["b", "a"])):
            with self.subTest(values=values):
                if values is None:
                    self.binding.pop("ids", None)
                else:
                    self.binding["ids"] = values
                result = self.assemble()
                self.assertEqual([item["id"] for item in result["planning"]["weather"]], expected)

    def test_task_and_file_bindings_preserve_valid_data_and_inputs(self):
        for source in ({"task": "synthetic"}, {"file": "state/weather.json"}):
            self.plan["collections"]["weather"] = {**source, "path": "entities.weather", "ids": ["ab"], "patches": {}, "append": []}
            before = (self.source.read_bytes(), self.file_source.read_bytes())
            result = self.assemble()
            self.assertEqual(result["planning"]["weather"][0]["summary"], "Synthetic weather ab")
            self.assertEqual((self.source.read_bytes(), self.file_source.read_bytes()), before)

    def test_custom_id_key_patches_and_appends_keep_order_and_do_not_mutate_inputs(self):
        extra = {"id": "extra", "summary": "Appended synthetic weather", "action_links": []}
        self.binding.update(id_key="code", ids=["code-b", "code-a"],
                            patches={"code-b": {"extension": {"replace": "changed"}}}, append=[extra])
        plan_before = copy.deepcopy(self.plan)
        source_before = self.source.read_bytes()
        result = self.assemble()
        weather = result["planning"]["weather"]
        self.assertEqual([item["id"] for item in weather], ["b", "a", "extra"])
        self.assertEqual(weather[0]["extension"], {"keep": "original", "replace": "changed"})
        self.assertEqual(weather[1]["extension"], {"keep": "original", "replace": "original"})
        self.assertEqual(self.plan, plan_before)
        self.assertEqual(self.source.read_bytes(), source_before)

    def test_empty_selection_still_allows_explicit_appends(self):
        self.binding.update(ids=[], append=[{"id": "extra", "summary": "Only appended", "action_links": []}])
        self.assertEqual([item["id"] for item in self.assemble()["planning"]["weather"]], ["extra"])

    def test_extension_collection_names_and_binding_fields_remain_supported(self):
        binding = {**self.binding, "ids": [], "note": "Synthetic extension", "append": [{"custom": True}]}
        result, _ = assembler.load_collections(self.workspace, {"collections": {"extension_collection": binding}})
        self.assertEqual(result, {"extension_collection": [{"custom": True}]})


if __name__ == "__main__":
    unittest.main()
