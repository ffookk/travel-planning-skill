from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout


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

    def assert_contained_failure(self, operation, message: str) -> None:
        read_text = Path.read_text
        read_bytes = Path.read_bytes

        def checked_read(method, path, *args, **kwargs):
            self.assertTrue(path.resolve().is_relative_to(self.workspace.resolve()), "Outside read attempted")
            return method(path, *args, **kwargs)

        with patch.object(Path, "read_text", autospec=True, side_effect=lambda path, *args, **kwargs: checked_read(read_text, path, *args, **kwargs)):
            with patch.object(Path, "read_bytes", autospec=True, side_effect=lambda path, *args, **kwargs: checked_read(read_bytes, path, *args, **kwargs)):
                with self.assertRaisesRegex(assemble_itinerary.AssemblyError, message) as raised:
                    operation()
        self.assertNotIn(str(self.workspace.parent), str(raised.exception))
        self.assertNotIn("SYNTHETIC-PRIVATE", str(raised.exception))

    def test_collection_files_cannot_read_outside_workspace(self) -> None:
        outside = self.workspace.parent / "private.json"
        write_json(outside, {"private": "SYNTHETIC-PRIVATE"})
        sibling = self.workspace.parent / "trip-sibling" / "private.json"
        write_json(sibling, {"private": "SYNTHETIC-PRIVATE"})
        (self.workspace / "state" / "external.json").symlink_to(outside)
        (self.workspace / "external-directory").symlink_to(sibling.parent, target_is_directory=True)
        references = (
            "../private.json", str(outside), "../trip-sibling/private.json",
            "state/external.json", "external-directory/private.json",
        )
        for reference in references:
            with self.subTest(reference=reference):
                self.plan["collections"]["attractions"] = {"file": reference, "path": "entities.attractions"}
                write_json(self.plan_path, self.plan)
                self.assert_contained_failure(
                    lambda: assemble_itinerary.assemble(self.workspace, self.plan_path),
                    "Collection file must resolve inside the workspace",
                )

    def test_internal_collection_paths_preserve_assembled_content(self) -> None:
        expected = assemble_itinerary.assemble(self.workspace, self.plan_path)
        result_path = self.workspace / "results" / "attractions.json"
        (self.workspace / "state" / "internal.json").symlink_to("../results/attractions.json")
        for reference in ("results/attractions.json", str(result_path), "state/internal.json", "state/../results/attractions.json"):
            with self.subTest(reference=reference):
                self.plan["collections"]["attractions"] = {
                    "file": reference, "path": "entities.attractions", "ids": ["museum"],
                }
                write_json(self.plan_path, self.plan)
                self.assertEqual(assemble_itinerary.assemble(self.workspace, self.plan_path), expected)

    def test_rejects_invalid_task_ids_before_reading_results(self) -> None:
        for task_id in ("../private", "/private", "nested/task", "nested\\task", "..", "Uppercase", "_prefix", "a" * 65, 123):
            with self.subTest(task_id=task_id):
                self.plan["collections"]["attractions"]["task"] = task_id
                with patch.object(assemble_itinerary, "read_json") as reader:
                    with self.assertRaisesRegex(assemble_itinerary.AssemblyError, "Task IDs must use"):
                        assemble_itinerary.load_collections(self.workspace, self.plan)
                    reader.assert_not_called()

    def test_valid_task_ids_and_internal_result_symlinks_remain_supported(self) -> None:
        expected = assemble_itinerary.assemble(self.workspace, self.plan_path)
        for task_id in ("task_1-test", "a" * 64):
            with self.subTest(task_id=task_id):
                (self.workspace / "results" / f"{task_id}.json").symlink_to("attractions.json")
                self.plan["collections"]["attractions"]["task"] = task_id
                write_json(self.plan_path, self.plan)
                self.assertEqual(assemble_itinerary.assemble(self.workspace, self.plan_path), expected)

    def test_result_symlink_cannot_read_outside_workspace(self) -> None:
        outside = self.workspace.parent / "private.json"
        write_json(outside, {"private": "SYNTHETIC-PRIVATE"})
        result_path = self.workspace / "results" / "attractions.json"
        result_path.unlink()
        result_path.symlink_to(outside)
        self.assert_contained_failure(
            lambda: assemble_itinerary.assemble(self.workspace, self.plan_path),
            "Task result must resolve inside the workspace",
        )

    def test_snapshot_references_cannot_read_outside_workspace(self) -> None:
        outside = self.workspace.parent / "private.json"
        write_json(outside, {"private": "SYNTHETIC-PRIVATE"})
        snapshot_directory = self.workspace / "snapshots" / "attractions"
        snapshot_directory.mkdir()
        (snapshot_directory / "linked.json").symlink_to(outside)
        for snapshot_id in ("../../../private", str(outside.with_suffix("")), "linked"):
            with self.subTest(snapshot_id=snapshot_id):
                tasks = {"attractions": {"source_snapshot_ids": [snapshot_id]}}
                self.assert_contained_failure(
                    lambda: assemble_itinerary.load_source_snapshots(self.workspace, tasks),
                    "Source snapshot must resolve inside the workspace",
                )
        with patch.object(assemble_itinerary, "read_json") as reader:
            with self.assertRaisesRegex(assemble_itinerary.AssemblyError, "Task IDs must use"):
                assemble_itinerary.load_source_snapshots(self.workspace, {"../private": {"source_snapshot_ids": ["id"]}})
            reader.assert_not_called()

    def test_internal_snapshot_symlink_preserves_snapshot(self) -> None:
        expected = {"snapshot_id": "synthetic", "items": [{"offer_id": "offer"}]}
        write_json(self.workspace / "state" / "snapshot.json", expected)
        snapshot_directory = self.workspace / "snapshots" / "attractions"
        snapshot_directory.mkdir()
        (snapshot_directory / "synthetic.json").symlink_to("../../state/snapshot.json")
        self.assertEqual(
            assemble_itinerary.load_source_snapshots(self.workspace, {"attractions": {"source_snapshot_ids": ["synthetic"]}}),
            [expected],
        )

    def test_source_file_symlink_cannot_read_outside_workspace(self) -> None:
        outside = self.workspace.parent / "private.jsonl"
        outside.write_text('{"private":"SYNTHETIC-PRIVATE"}\n', encoding="utf-8")
        (self.workspace / "sources" / "linked.jsonl").symlink_to(outside)
        self.assert_contained_failure(
            lambda: assemble_itinerary.collect_sources(self.workspace),
            "Source file must resolve inside the workspace",
        )

    def test_source_directory_symlink_is_rejected_before_enumeration(self) -> None:
        source_directory = self.workspace / "sources"
        source_directory.rmdir()
        source_directory.symlink_to(self.workspace.parent, target_is_directory=True)
        with patch.object(Path, "glob") as enumerate_sources:
            self.assert_contained_failure(
                lambda: assemble_itinerary.collect_sources(self.workspace),
                "Source directory must resolve inside the workspace",
            )
            enumerate_sources.assert_not_called()

    def test_missing_optional_source_directory_remains_empty(self) -> None:
        (self.workspace / "sources").rmdir()
        self.assertEqual(assemble_itinerary.collect_sources(self.workspace), [])

    def test_internal_source_directory_and_file_symlinks_remain_supported(self) -> None:
        stored_sources = self.workspace / "state" / "source-store"
        stored_sources.mkdir()
        source = {"id": "source-1", "title": "Synthetic source", "url": "https://example.com/", "summary": "Public summary"}
        (self.workspace / "state" / "source-record.jsonl").write_text(json.dumps(source) + "\n", encoding="utf-8")
        (stored_sources / "linked.jsonl").symlink_to("../source-record.jsonl")
        (self.workspace / "sources").rmdir()
        (self.workspace / "sources").symlink_to("state/source-store", target_is_directory=True)
        result = assemble_itinerary.collect_sources(self.workspace)
        self.assertEqual(result, [{"id": "source-1", "title": "Synthetic source", "url": "https://example.com/", "note": "Public summary", "checked_at": None}])

    def test_route_and_research_state_symlinks_cannot_escape_workspace(self) -> None:
        outside = self.workspace.parent / "private.json"
        write_json(outside, {"private": "SYNTHETIC-PRIVATE"})
        for relative, label in (("selected-route.json", "Selected route"), ("state/research.json", "Research state")):
            with self.subTest(relative=relative):
                path = self.workspace / relative
                original = path.read_bytes()
                path.unlink()
                path.symlink_to(outside)
                self.assert_contained_failure(
                    lambda: assemble_itinerary.assemble(self.workspace, self.plan_path),
                    f"{label} must resolve inside the workspace",
                )
                path.unlink()
                path.write_bytes(original)

    def test_default_plan_symlink_is_rejected_before_read(self) -> None:
        outside = self.workspace.parent / "private.json"
        write_json(outside, {"private": "SYNTHETIC-PRIVATE"})
        self.plan_path.unlink()
        self.plan_path.symlink_to(outside)
        with patch("sys.argv", ["assemble_itinerary.py", "--workspace", str(self.workspace)]):
            self.assert_contained_failure(assemble_itinerary.main, "Default plan must resolve inside the workspace")
        self.assertFalse((self.workspace / "artifacts" / "itinerary.json").exists())

    def test_research_digest_command_rejects_external_symlink(self) -> None:
        outside = self.workspace.parent / "private.json"
        write_json(outside, {"private": "SYNTHETIC-PRIVATE"})
        research_path = self.workspace / "state" / "research.json"
        research_path.unlink()
        research_path.symlink_to(outside)
        with patch("sys.argv", ["assemble_itinerary.py", "--workspace", str(self.workspace), "--print-research-sha256"]):
            self.assert_contained_failure(assemble_itinerary.main, "Research state must resolve inside the workspace")

    def test_default_cli_and_explicit_external_plan_and_output_remain_supported(self) -> None:
        expected = assemble_itinerary.assemble(self.workspace, self.plan_path)
        with patch("sys.argv", ["assemble_itinerary.py", "--workspace", str(self.workspace)]), redirect_stdout(io.StringIO()):
            self.assertEqual(assemble_itinerary.main(), 0)
        default_output = self.workspace / "artifacts" / "itinerary.json"
        self.assertEqual(json.loads(default_output.read_text(encoding="utf-8")), expected)
        explicit_plan = self.workspace.parent / "explicit-plan.json"
        write_json(explicit_plan, self.plan)
        explicit_output = self.workspace.parent / "explicit-output.json"
        arguments = ["assemble_itinerary.py", "--workspace", str(self.workspace), "--plan", str(explicit_plan), "--output", str(explicit_output)]
        with patch("sys.argv", arguments), redirect_stdout(io.StringIO()):
            self.assertEqual(assemble_itinerary.main(), 0)
        self.assertEqual(json.loads(explicit_output.read_text(encoding="utf-8")), expected)

    def test_internal_default_plan_and_state_symlinks_preserve_output(self) -> None:
        expected = assemble_itinerary.assemble(self.workspace, self.plan_path)
        for relative in ("selected-route.json", "state/research.json", "state/itinerary-plan.json"):
            path = self.workspace / relative
            stored = path.with_name(f"stored-{path.name}")
            path.rename(stored)
            path.symlink_to(stored.name)
        with patch("sys.argv", ["assemble_itinerary.py", "--workspace", str(self.workspace)]), redirect_stdout(io.StringIO()):
            self.assertEqual(assemble_itinerary.main(), 0)
        result = json.loads((self.workspace / "artifacts" / "itinerary.json").read_text(encoding="utf-8"))
        self.assertEqual(result, expected)

    def test_cyclic_collection_symlink_has_a_path_free_error(self) -> None:
        (self.workspace / "state" / "first.json").symlink_to("second.json")
        (self.workspace / "state" / "second.json").symlink_to("first.json")
        self.plan["collections"]["attractions"] = {"file": "state/first.json", "path": "entities.attractions"}
        with patch.object(assemble_itinerary, "read_json") as reader:
            with self.assertRaisesRegex(assemble_itinerary.AssemblyError, "Collection file must resolve inside the workspace") as raised:
                assemble_itinerary.load_collections(self.workspace, self.plan)
            reader.assert_not_called()
        self.assertNotIn(str(self.workspace), str(raised.exception))

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


if __name__ == "__main__":
    unittest.main()
