from __future__ import annotations

import copy
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch


SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "travel-planning"


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


finalizer = load_module("finalize_itinerary")
assembler = load_module("assemble_itinerary")


class FinalizeItineraryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.input = self.root / "itinerary.json"
        self.output = self.root / "itinerary.html"
        self.report = self.root / "receipt.json"
        self.workspace = self.root / "workspace"
        (self.workspace / "state").mkdir(parents=True)
        self.research_path = self.workspace / "state" / "research.json"
        self.decisions_path = self.root / "decisions.json"
        self.data = json.loads((SKILL_ROOT / "assets" / "example-itinerary.json").read_text(encoding="utf-8"))
        self.data["workflow"]["phase"] = "final"
        self.write(self.input, self.data)
        self.research = {"schema_version": "travel-research-state/v2", "global_state": {"shared_entities": [], "conflicts": []}}
        self.write(self.research_path, self.research)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def run_final(self, **kwargs):
        return finalizer.finalize(self.input, self.output, self.report, **kwargs)

    def conflict(self, entity_id: str = "a1") -> dict:
        value = self.data["planning"]["attractions"][0]["name"]
        return {"entity_id": entity_id, "field": "canonical_name", "previous_value": value,
                "incoming_value": "Other synthetic name", "selected_value": "Other synthetic name",
                "previous_task_ids": ["official"], "incoming_task_id": "community", "resolution": "latest_submission_wins"}

    def set_conflicts(self, *conflicts: dict) -> None:
        self.research["global_state"]["conflicts"] = list(conflicts)
        self.write(self.research_path, self.research)

    def decisions(self, conflict: dict) -> dict:
        return {"schema_version": "itinerary-conflict-decisions/v1",
                "itinerary_sha256": finalizer.digest(self.input.read_bytes()),
                "research_sha256": finalizer.digest(self.research_path.read_bytes()), "entity_usage": [],
                "decisions": [{"conflict_sha256": finalizer.digest(finalizer.canonical(conflict)),
                               "selected_value": conflict["previous_value"], "itinerary_pointer": "/planning/attractions/0/name",
                               "reason": "Retain the applicable official identity", "source_ids": [self.data["sources"][0]["id"]]}]}

    def assert_preserved(self, operation) -> None:
        self.output.write_bytes(b"existing HTML")
        self.report.write_bytes(b"existing receipt")
        with self.assertRaises(finalizer.FinalizationError):
            operation()
        self.assertEqual(self.output.read_bytes(), b"existing HTML")
        self.assertEqual(self.report.read_bytes(), b"existing receipt")
        self.assertEqual(list(self.root.glob(".final-delivery-*")), [])

    def test_success_binds_exact_input_html_and_report_without_payload_or_paths(self) -> None:
        before = self.input.read_bytes()
        report = self.run_final()
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["itinerary_sha256"], finalizer.digest(before))
        self.assertEqual(report["html_sha256"], finalizer.digest(self.output.read_bytes()))
        binding = {key: report[key] for key in ("itinerary_sha256", "html_sha256", "research_sha256", "decisions_sha256", "export_profile")}
        self.assertEqual(report["binding_sha256"], finalizer.digest(finalizer.canonical(binding)))
        self.assertEqual(json.loads(self.report.read_bytes()), report)
        self.assertEqual(report["conflicts"]["status"], "conflicts_not_checked")
        self.assertEqual(report["export_profile"], "regular")
        self.assertNotIn(self.data["trip"]["title"], self.report.read_text())
        self.assertNotIn(str(self.root), self.report.read_text())
        self.assertEqual(self.input.read_bytes(), before)
        self.assertEqual(self.run_final()["binding_sha256"], report["binding_sha256"])

    def test_audits_and_renders_the_same_loaded_object_once(self) -> None:
        actual_audit = finalizer.audit_itinerary.audit
        actual_build = finalizer.audit_itinerary.render_itinerary.build
        objects = []
        def auditing(data):
            objects.append(data)
            self.input.write_bytes(b"changed after load")
            return actual_audit(data)
        def rendering(data):
            self.assertIs(data, objects[0])
            return actual_build(data)
        original_sha = finalizer.digest(self.input.read_bytes())
        with patch.object(finalizer.audit_itinerary, "audit", side_effect=auditing) as audit, patch.object(finalizer.audit_itinerary.render_itinerary, "build", side_effect=rendering) as render:
            report = self.run_final()
        self.assertEqual(audit.call_count, 1)
        self.assertEqual(render.call_count, 1)
        self.assertEqual(report["itinerary_sha256"], original_sha)

    def test_unsupported_offline_profile_preserves_outputs_without_regular_fallback(self) -> None:
        calls = []
        def regular_only(data):
            calls.append(data)
            return "<!doctype html><html>Regular</html>"
        with patch.object(finalizer.audit_itinerary.render_itinerary, "build", new=regular_only):
            self.assert_preserved(lambda: self.run_final(private_offline=True))
        self.assertEqual(calls, [])

    def test_offline_profile_delegates_explicitly_and_binds_profile_to_receipt(self) -> None:
        calls = []
        def offline_capable(data, *, private_offline=False):
            calls.append((data, private_offline))
            return "<!doctype html><html>Audited synthetic offline document</html>"
        with patch.object(finalizer.audit_itinerary.render_itinerary, "build", new=offline_capable):
            report = self.run_final(private_offline=True)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0][1])
        self.assertEqual(calls[0][0], self.data)
        self.assertEqual(report["export_profile"], "private-offline")
        self.assertEqual(report["html_sha256"], finalizer.digest(self.output.read_bytes()))

    def test_overlap_blocks_delivery_but_original_renderer_still_supports_preview(self) -> None:
        self.data["days"][0]["events"][2]["time"] = "10:00"
        self.write(self.input, self.data)
        self.assertTrue(finalizer.audit_itinerary.render_itinerary.build(self.data).startswith("<!doctype html>"))
        with patch.object(finalizer.audit_itinerary.render_itinerary, "build") as render:
            self.assert_preserved(self.run_final)
        render.assert_not_called()

    def test_draft_and_missing_final_readiness_do_not_get_promoted(self) -> None:
        for change in ("draft", "readiness"):
            with self.subTest(change=change):
                data = copy.deepcopy(self.data)
                if change == "draft":
                    data["workflow"]["phase"] = "confirmed_planning"
                else:
                    data["planning"] = {}
                self.write(self.input, data)
                self.assert_preserved(self.run_final)

    def test_final_expired_selected_inventory_blocks_delivery(self) -> None:
        snapshot_id = "0123456789abcdef01234567"
        self.data["planning"]["source_snapshots"] = [{
            "schema_version": "travel-source-snapshot/v1", "snapshot_id": snapshot_id,
            "snapshot_kind": "operational", "status": "platform_reported", "provider": {"id": "synthetic", "name": "Synthetic"},
            "product_type": "flight", "tool": "synthetic", "query": {},
            "freshness": {"checked_at": "2000-01-01T00:00:00+00:00", "expires_at": "2000-01-01T01:00:00+00:00", "dynamic": True},
            "items": [{"offer_id": "flight", "name": "Synthetic flight", "price": {"display": "¥0"}, "availability": {}, "action_link": None}],
            "count": 1, "raw_response_hash": "sha256:" + "a" * 64,
            "source": {"title": "Synthetic", "url": "https://example.com", "kind": "official_platform_api"}, "disclaimer": "Recheck",
        }]
        self.data["planning"]["transport_edges"][0]["inventory_refs"] = [{"snapshot_id": snapshot_id, "offer_id": "flight", "role": "operational_check"}]
        self.write(self.input, self.data)
        self.assertTrue(finalizer.audit_itinerary.audit(self.data)["inventory_audit"]["expired_snapshot_ids"])
        self.assert_preserved(self.run_final)

    def test_assembly_provenance_requires_matching_workspace(self) -> None:
        (self.workspace / "sources").mkdir()
        self.write(self.workspace / "selected-route.json", {"id": "route"})
        plan = {"schema_version": "itinerary-plan/v1", "research_state_sha256": finalizer.digest(self.research_path.read_bytes()),
                "trip": {"title": "Synthetic"}, "workflow": {"phase": "final", "selected_route_id": "route"},
                "collections": {}, "days": [{"date": "2026-10-03", "events": []}]}
        plan_path = self.workspace / "state" / "plan.json"
        self.write(plan_path, plan)
        assembled = assembler.assemble(self.workspace, plan_path)
        self.assertEqual(assembled["research_context"]["research_state_sha256"], plan["research_state_sha256"])
        self.assertNotIn(str(self.workspace), json.dumps(assembled["research_context"]))
        self.data["research_context"] = assembled["research_context"]
        self.write(self.input, self.data)
        self.assert_preserved(self.run_final)
        report = self.run_final(workspace=self.workspace)
        self.assertEqual(report["research_sha256"], plan["research_state_sha256"])
        self.write(self.research_path, {**self.research, "changed": True})
        self.assert_preserved(lambda: self.run_final(workspace=self.workspace))

    def test_used_conflict_requires_decision_even_when_merge_marked_it_resolved(self) -> None:
        conflict = self.conflict()
        self.set_conflicts(conflict)
        self.assert_preserved(lambda: self.run_final(workspace=self.workspace))
        decisions = self.decisions(conflict)
        self.write(self.decisions_path, decisions)
        report = self.run_final(workspace=self.workspace, decisions_path=self.decisions_path)
        self.assertEqual(report["conflicts"]["resolved_conflict_count"], 1)
        self.assertEqual(report["decisions_sha256"], finalizer.digest(self.decisions_path.read_bytes()))
        self.assertEqual(json.loads(self.input.read_bytes()), self.data)

    def test_unreferenced_candidate_conflict_does_not_block(self) -> None:
        candidate = copy.deepcopy(self.data["planning"]["attractions"][0])
        candidate["id"] = "unused-candidate"
        self.data["planning"]["attractions"].append(candidate)
        self.write(self.input, self.data)
        self.set_conflicts(self.conflict("unused-candidate"))
        report = self.run_final(workspace=self.workspace)
        self.assertEqual(report["conflicts"], {"status": "checked", "resolved_conflict_count": 0, "unused_conflict_count": 1})

    def test_unmapped_conflict_requires_explicit_usage_and_used_mapping_is_checked(self) -> None:
        conflict = self.conflict("shared-attraction")
        self.set_conflicts(conflict)
        self.assert_preserved(lambda: self.run_final(workspace=self.workspace))
        decisions = self.decisions(conflict)
        decisions["entity_usage"] = [{"entity_id": "shared-attraction", "usage": "used", "itinerary_pointer": "/planning/attractions/0", "reason": "Same selected attraction"}]
        self.write(self.decisions_path, decisions)
        self.assertEqual(self.run_final(workspace=self.workspace, decisions_path=self.decisions_path)["conflicts"]["resolved_conflict_count"], 1)
        decisions["entity_usage"] = [{"entity_id": "shared-attraction", "usage": "unused", "reason": "Different unselected candidate"}]
        decisions["decisions"] = []
        self.write(self.decisions_path, decisions)
        self.assertEqual(self.run_final(workspace=self.workspace, decisions_path=self.decisions_path)["conflicts"]["unused_conflict_count"], 1)

    def test_cannot_waive_a_referenced_entity_as_unused(self) -> None:
        conflict = self.conflict()
        self.set_conflicts(conflict)
        decisions = self.decisions(conflict)
        decisions["entity_usage"] = [{"entity_id": "a1", "usage": "unused", "reason": "Synthetic incorrect declaration"}]
        self.write(self.decisions_path, decisions)
        self.assert_preserved(lambda: self.run_final(workspace=self.workspace, decisions_path=self.decisions_path))

    def test_decision_cannot_point_at_unrelated_field_with_same_value(self) -> None:
        attraction = self.data["planning"]["attractions"][0]
        attraction["opening_hours"] = "09:00-17:00"
        attraction["unrelated_note"] = "09:00-17:00"
        self.write(self.input, self.data)
        conflict = {**self.conflict(), "field": "facts.opening_hours", "previous_value": "09:00-17:00", "incoming_value": "09:00-18:00"}
        self.set_conflicts(conflict)
        decisions = self.decisions(conflict)
        decisions["decisions"][0]["itinerary_pointer"] = "/planning/attractions/0/unrelated_note"
        self.write(self.decisions_path, decisions)
        self.assert_preserved(lambda: self.run_final(workspace=self.workspace, decisions_path=self.decisions_path))
        decisions["decisions"][0]["itinerary_pointer"] = "/planning/attractions/0/opening_hours"
        self.write(self.decisions_path, decisions)
        self.assertEqual(self.run_final(workspace=self.workspace, decisions_path=self.decisions_path)["conflicts"]["resolved_conflict_count"], 1)

    def test_repeated_field_history_accepts_one_coherent_final_value_for_all_records(self) -> None:
        first = self.conflict()
        second = {**first, "previous_value": first["incoming_value"], "incoming_value": "Final synthetic name", "selected_value": "Final synthetic name"}
        self.data["planning"]["attractions"][0]["name"] = second["incoming_value"]
        self.write(self.input, self.data)
        self.set_conflicts(first, second)
        decisions = self.decisions(first)
        decisions["decisions"][0]["selected_value"] = second["incoming_value"]
        decisions["decisions"].append({**decisions["decisions"][0], "conflict_sha256": finalizer.digest(finalizer.canonical(second))})
        self.write(self.decisions_path, decisions)
        self.assertEqual(self.run_final(workspace=self.workspace, decisions_path=self.decisions_path)["conflicts"]["resolved_conflict_count"], 2)
        decisions["decisions"].pop()
        self.write(self.decisions_path, decisions)
        self.assert_preserved(lambda: self.run_final(workspace=self.workspace, decisions_path=self.decisions_path))

    def test_referenced_duplicate_ids_cannot_disagree_with_renderers_last_item(self) -> None:
        duplicate = copy.deepcopy(self.data["planning"]["attractions"][0])
        duplicate["name"] = "Later duplicate name"
        self.data["planning"]["attractions"].append(duplicate)
        self.write(self.input, self.data)
        conflict = self.conflict()
        self.set_conflicts(conflict)
        self.write(self.decisions_path, self.decisions(conflict))
        self.assert_preserved(lambda: self.run_final(workspace=self.workspace, decisions_path=self.decisions_path))
        self.data["planning"]["attractions"].pop()
        self.data["planning"]["attractions"][0]["entity_id"] = "a1"
        self.write(self.input, self.data)
        self.write(self.decisions_path, self.decisions(conflict))
        self.assertEqual(self.run_final(workspace=self.workspace, decisions_path=self.decisions_path)["conflicts"]["resolved_conflict_count"], 1)

    def test_missing_recorded_conflict_values_fail_closed(self) -> None:
        for field in ("previous_value", "incoming_value"):
            with self.subTest(field=field):
                conflict = self.conflict("unmapped-candidate")
                del conflict[field]
                self.set_conflicts(conflict)
                self.assert_preserved(lambda: self.run_final(workspace=self.workspace))

    def test_stale_or_mismatched_conflict_decisions_fail_closed(self) -> None:
        conflict = self.conflict()
        self.set_conflicts(conflict)
        valid = self.decisions(conflict)
        invalid = []
        for field in ("itinerary_sha256", "research_sha256"):
            item = copy.deepcopy(valid)
            item[field] = "0" * 64
            invalid.append(item)
        for field, value in (("conflict_sha256", "0" * 64), ("selected_value", conflict["incoming_value"]),
                             ("itinerary_pointer", "/trip/title"), ("source_ids", ["unregistered"]), ("reason", "")):
            item = copy.deepcopy(valid)
            item["decisions"][0][field] = value
            invalid.append(item)
        for item in invalid:
            with self.subTest(item=item):
                self.write(self.decisions_path, item)
                self.assert_preserved(lambda: self.run_final(workspace=self.workspace, decisions_path=self.decisions_path))

    def test_report_and_input_targets_cannot_alias(self) -> None:
        before = self.input.read_bytes()
        with self.assertRaises(finalizer.FinalizationError):
            finalizer.finalize(self.input, self.input, self.report)
        with self.assertRaises(finalizer.FinalizationError):
            finalizer.finalize(self.input, self.output, self.output)
        self.assertEqual(self.input.read_bytes(), before)

    def test_second_replacement_failure_restores_both_existing_outputs(self) -> None:
        self.output.write_bytes(b"existing HTML")
        self.report.write_bytes(b"existing receipt")
        if os.name == "posix":
            self.output.chmod(0o604)
            self.report.chmod(0o640)
        replace = os.replace
        calls = 0
        def fail_once(source, target):
            nonlocal calls
            if os.name == "posix":
                self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in self.root.glob(".final-delivery-*")))
            calls += 1
            if calls == 2:
                raise OSError("synthetic replacement failure")
            return replace(source, target)
        with patch.object(finalizer.os, "replace", side_effect=fail_once):
            self.assert_preserved(self.run_final)
        if os.name == "posix":
            self.assertEqual(self.output.stat().st_mode & 0o777, 0o604)
            self.assertEqual(self.report.stat().st_mode & 0o777, 0o640)

    @unittest.skipUnless(os.name == "posix", "Owner-only POSIX mode contract")
    def test_successful_delivery_replaces_public_modes_with_owner_only_files(self) -> None:
        self.output.write_bytes(b"existing HTML")
        self.report.write_bytes(b"existing receipt")
        self.output.chmod(0o644)
        self.report.chmod(0o664)
        self.run_final()
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.report.stat().st_mode & 0o777, 0o600)

    def test_non_posix_rollback_preserves_bytes_without_fchmod(self) -> None:
        replace = os.replace
        calls = 0
        def fail_once(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("synthetic replacement failure")
            return replace(source, target)
        with patch.object(finalizer, "os", wraps=os) as platform_os:
            platform_os.name = "nt"
            platform_os.fchmod = Mock(side_effect=AssertionError("POSIX permissions must not be used"))
            platform_os.replace.side_effect = fail_once
            self.assert_preserved(self.run_final)
            platform_os.fchmod.assert_not_called()
        self.assertEqual(calls, 3)

    def test_failed_rollback_keeps_original_backups_for_local_recovery(self) -> None:
        self.output.write_bytes(b"original HTML for recovery")
        self.report.write_bytes(b"original receipt for recovery")
        replace = os.replace
        calls = 0
        def fail_publication_and_rollback(source, target):
            nonlocal calls
            calls += 1
            if calls in (2, 3):
                raise OSError("synthetic recovery failure")
            return replace(source, target)
        with patch.object(finalizer.os, "replace", side_effect=fail_publication_and_rollback):
            with self.assertRaisesRegex(finalizer.FinalizationError, "recovery backups remain") as raised:
                self.run_final()
        backups = list(self.root.glob(".final-delivery-*"))
        self.assertEqual({path.read_bytes() for path in backups}, {b"original HTML for recovery", b"original receipt for recovery"})
        if os.name == "posix":
            self.assertTrue(all(path.stat().st_mode & 0o777 == 0o600 for path in backups))
        self.assertNotIn(str(self.root), str(raised.exception))

    def test_nonfinite_json_is_rejected_without_overwriting_outputs(self) -> None:
        self.data["unexpected_amount"] = float("nan")
        self.write(self.input, self.data)
        self.assert_preserved(self.run_final)

    def test_rendering_mutation_or_failure_never_publishes_a_misbound_artifact(self) -> None:
        def mutate(data):
            data["trip"]["title"] = "Changed during rendering"
            return "<html>Changed</html>"
        with patch.object(finalizer.audit_itinerary.render_itinerary, "build", side_effect=mutate):
            self.assert_preserved(self.run_final)
        with patch.object(finalizer.audit_itinerary.render_itinerary, "build", side_effect=ValueError("synthetic")):
            self.assert_preserved(self.run_final)

    def test_research_symlink_escape_and_output_symlink_are_rejected(self) -> None:
        outside = self.root / "outside-research.json"
        self.write(outside, self.research)
        self.research_path.unlink()
        self.research_path.symlink_to(outside)
        self.assert_preserved(lambda: self.run_final(workspace=self.workspace))
        self.output.unlink()
        self.output.symlink_to(outside)
        before = outside.read_bytes()
        with self.assertRaises(finalizer.FinalizationError):
            self.run_final()
        self.assertEqual(outside.read_bytes(), before)
        self.assertEqual(self.report.read_bytes(), b"existing receipt")

    def test_malformed_input_and_runtime_errors_do_not_log_payloads_or_paths(self) -> None:
        secret = "SYNTHETIC-DO-NOT-LOG"
        self.input.write_text('{"private":"' + secret + '",', encoding="utf-8")
        for bad_audit in (False, True):
            if bad_audit:
                self.write(self.input, self.data)
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(finalizer.sys, "argv", ["finalize", str(self.input), str(self.output), "--report", str(self.report)]), redirect_stdout(stdout), redirect_stderr(stderr):
                if bad_audit:
                    with patch.object(finalizer.audit_itinerary, "audit", side_effect=TypeError(secret)):
                        status = finalizer.main()
                else:
                    status = finalizer.main()
            self.assertEqual(status, 1)
            self.assertNotIn(secret, stdout.getvalue() + stderr.getvalue())
            self.assertNotIn(str(self.root), stdout.getvalue() + stderr.getvalue())
            self.assertFalse(self.output.exists())
            self.assertFalse(self.report.exists())


if __name__ == "__main__":
    unittest.main()
