from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/travel-planning/scripts"


def load(name):
    spec = importlib.util.spec_from_file_location("cost_shape_" + name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


auditor = load("audit_itinerary")


class CostInputShapesTest(unittest.TestCase):
    def invalid_inputs(self):
        return (
            [], {"trip": "SYNTHETIC-PRIVATE"}, {"planning": []},
            {"days": "SYNTHETIC-PRIVATE"}, {"days": [None]},
            {"days": [{"events": "SYNTHETIC-PRIVATE"}]},
            {"days": [{"events": [None]}]},
            {"days": [{"events": [{"cost_items": {}}]}]},
            {"days": [{"events": [{"cost_items": [None]}]}]},
            {"planning": {"transport_edges": [None]}},
            {"planning": {"intercity_options": "SYNTHETIC-PRIVATE"}},
        )

    def test_cost_audit_rejects_invalid_container_shapes_without_mutation(self):
        for data in self.invalid_inputs():
            with self.subTest(data=data):
                before = copy.deepcopy(data)
                errors, warnings = auditor.cost_contract.audit_costs(data)
                self.assertEqual(len(errors), 1)
                self.assertEqual(warnings, [])
                self.assertNotIn("SYNTHETIC-PRIVATE", errors[0])
                self.assertEqual(data, before)

    def test_itinerary_audit_returns_structured_failure_before_other_checks(self):
        for data in self.invalid_inputs():
            with self.subTest(data=data), patch.object(auditor.render_itinerary, "validate_data") as validate:
                result = auditor.audit(data)
                self.assertEqual(result["status"], "fail")
                self.assertEqual(len(result["blocking"]), 1)
                self.assertEqual(result["checked_event_ids"], [])
                self.assertNotIn("SYNTHETIC-PRIVATE", json.dumps(result))
                validate.assert_not_called()

    def test_missing_or_null_optional_cost_containers_remain_supported(self):
        for data in ({}, {"trip": None, "planning": None, "days": None},
                     {"days": [{"events": None}]},
                     {"planning": {"transport_edges": None, "intercity_options": []},
                      "days": [{"events": [{"type": "note", "cost_items": None}]}]}):
            with self.subTest(data=data):
                self.assertEqual(auditor.cost_contract.audit_costs(data), ([], []))

    def test_cli_reports_invalid_day_as_json_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "SYNTHETIC-PRIVATE-input.json"
            source.write_text(json.dumps({"days": [None]}), encoding="utf-8")
            output = io.StringIO()
            with patch.object(sys, "argv", ["audit_itinerary.py", str(source)]), contextlib.redirect_stdout(output):
                with self.assertRaises(SystemExit) as stopped:
                    auditor.main()
            self.assertEqual(stopped.exception.code, 1)
            self.assertEqual(json.loads(output.getvalue())["status"], "fail")
            self.assertNotIn("SYNTHETIC-PRIVATE", output.getvalue())

    def test_malformed_final_document_is_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, html, receipt = (root / name for name in ("SYNTHETIC-PRIVATE.json", "page.html", "receipt.json"))
            data = {"workflow": {"phase": "final"}, "planning": {"readiness": [{}]},
                    "trip": {"title": "SYNTHETIC-PRIVATE"}, "days": [None]}
            source.write_text(json.dumps(data), encoding="utf-8")
            before = source.read_bytes()
            result = auditor.audit(json.loads(source.read_bytes()))
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["blocking"], ["Itinerary days must be an array of objects"])
            # Exercise the independent finalizer as well when both features are installed.
            if (SCRIPTS / "finalize_itinerary.py").exists():
                finalizer = load("finalize_itinerary")
                output, errors = io.StringIO(), io.StringIO()
                with patch.object(sys, "argv", ["finalize_itinerary.py", str(source), str(html), "--report", str(receipt)]), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                    self.assertEqual(finalizer.main(), 1)
                self.assertIn("Audit found blocking issues", errors.getvalue())
                self.assertNotIn("SYNTHETIC-PRIVATE", errors.getvalue())
                self.assertNotIn("Traceback", errors.getvalue())
                self.assertEqual(output.getvalue(), "")
            self.assertEqual(source.read_bytes(), before)
            self.assertFalse(html.exists())
            self.assertFalse(receipt.exists())


if __name__ == "__main__":
    unittest.main()
