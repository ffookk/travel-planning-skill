from __future__ import annotations

import contextlib
import copy
import decimal
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL = Path(__file__).resolve().parents[1] / "skills/travel-planning"
SPEC = importlib.util.spec_from_file_location("planning_evaluation", SKILL / "scripts/evaluate_planning_case.py")
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)
DIGEST = "0" * 64


def fact(value, unit="boolean", status="verified"):
    return {"description": "Synthetic fact for this test only", "value": value, "unit": unit, "status": status}


def fixture():
    return {"schema": "planning-case/v1", "id": "synthetic-access", "prompt": "Choose an evidenced accessible route.",
            "facts": {"east-access": fact(False), "west-access": fact(None, status="unknown"), "bus-access": fact(True),
                      "departure": fact(1080, "minutes"), "walk": fact(35, "minutes"), "buffer": fact(15, "minutes")},
            "rules": [
                {"id": "route", "kind": "choice", "minimum": 1, "maximum": 1, "policy": "feasible",
                 "options": [{"id": mode, "requires": [{"fact": mode + "-access", "equals": True}]}
                             for mode in ("east", "west", "bus")]},
                {"id": "unknowns", "kind": "pending", "facts": ["east-access", "west-access", "bus-access"]},
                {"id": "leave-by", "kind": "quantity", "expression": {"op": "sum", "args": [
                    {"fact": "departure"}, {"op": "scale", "factor": -1, "arg": {"fact": "walk"}},
                    {"op": "scale", "factor": -1, "arg": {"fact": "buffer"}}]}}], "examples": []}


def response(answers=None):
    return {"schema": "planning-answer/v1", "case_id": "synthetic-access", "case_sha256": DIGEST,
            "answers": answers or {"route": ["bus"], "unknowns": ["west-access"], "leave-by": {"value": 1030, "unit": "minutes"}}}


class PlanningEvaluationTest(unittest.TestCase):
    def setUp(self):
        self.case = fixture()
        self.answer = response()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def score(self):
        return evaluation.evaluate(self.case, self.answer, DIGEST)["result"]

    def test_supported_choice_and_computed_deadline(self):
        self.assertEqual(self.score(), "pass")
        self.case["facts"]["departure"]["value"] += 30
        self.assertEqual(self.score(), "fail")
        self.answer["answers"]["leave-by"]["value"] += 30
        self.assertEqual(self.score(), "pass")

    def test_unknown_and_verified_negative_are_not_eligible(self):
        for route in ("west", "east"):
            self.answer["answers"]["route"] = [route]
            self.assertEqual(self.score(), "fail")

    def test_loss_of_evidence_requires_deferral(self):
        self.case["facts"]["bus-access"] = fact(None, status="unknown")
        self.answer["answers"]["unknowns"].append("bus-access")
        self.assertEqual(self.score(), "fail")
        self.answer["answers"]["route"] = []
        self.assertEqual(self.score(), "pass")

    def test_missing_or_invented_pending_fact_fails(self):
        for pending in ([], ["east-access", "west-access"]):
            self.answer["answers"]["unknowns"] = pending
            self.assertEqual(self.score(), "fail")

    def test_rule_fact_and_option_order_do_not_change_result(self):
        self.case["rules"].reverse()
        self.case["facts"] = dict(reversed(list(self.case["facts"].items())))
        self.case["rules"][-1]["options"].reverse()
        self.assertEqual(self.score(), "pass")

    def test_unknown_quantity_must_be_explicit_and_unit_kept(self):
        self.case["facts"]["walk"] = fact(None, "minutes", "unknown")
        self.assertEqual(self.score(), "fail")
        self.answer["answers"]["leave-by"]["value"] = None
        self.assertEqual(self.score(), "pass")
        self.answer["answers"]["leave-by"]["unit"] = "AUD"
        self.assertEqual(self.score(), "fail")

    def test_cheapest_comparison_handles_caps_ties_and_unknown_totals(self):
        self.case["facts"].update({"fare-a": fact(12, "AUD"), "fare-b": fact(8, "AUD"), "cap": fact(15, "AUD"), "pass": fact(18, "AUD")})
        capped = {"op": "min", "args": [{"op": "sum", "args": [{"fact": "fare-a"}, {"fact": "fare-b"}]}, {"fact": "cap"}]}
        self.case["rules"][0] = {"id": "route", "kind": "choice", "minimum": 1, "maximum": 1, "policy": "cheapest",
                                 "options": [{"id": "bus", "requires": [], "cost": capped},
                                             {"id": "pass", "requires": [], "cost": {"fact": "pass"}}]}
        self.assertEqual(self.score(), "pass")
        self.answer["answers"]["route"] = ["pass"]
        self.assertEqual(self.score(), "fail")
        self.case["facts"]["pass"]["value"] = 15
        self.assertEqual(self.score(), "pass")
        self.case["facts"]["cap"] = fact(None, "AUD", "unknown")
        self.assertEqual(self.score(), "fail")
        self.answer["answers"]["route"] = []
        self.assertEqual(self.score(), "pass")

    def test_numeric_eligibility_checks_the_complete_time_chain(self):
        self.case["facts"]["retrieval"] = fact(20, "minutes")
        test = {"left": {"op": "sum", "args": [{"fact": "walk"}, {"fact": "retrieval"}]},
                "op": "le", "right": {"fact": "buffer"}}
        self.case["rules"][0]["options"][2]["requires"].append(test)
        self.assertEqual(self.score(), "fail")
        self.case["facts"]["retrieval"]["value"] = 0
        self.case["facts"]["buffer"]["value"] = 35
        self.answer["answers"]["leave-by"]["value"] = 1010
        self.assertEqual(self.score(), "pass")

    def test_typed_expression_rejects_mixed_units_and_unsupported_operators(self):
        for expression in ({"op": "exec", "args": []}, {"fact": "missing"}, {"fact": "east-access"},
                           {"op": "sum", "args": []}, {"op": "scale", "factor": True, "arg": {"fact": "walk"}}):
            self.case["rules"][-1]["expression"] = expression
            with self.assertRaises(evaluation.InputError):
                self.score()
        self.case = fixture()
        self.case["facts"]["walk"]["unit"] = "AUD"
        with self.assertRaises(evaluation.InputError):
            self.score()

    def test_candidate_contract_rejects_unknown_fields_references_and_stale_hashes(self):
        mutations = [lambda a: a.update(case_sha256="1" * 64), lambda a: a.update(schema="planning-answer/v2"),
                     lambda a: a["answers"].update(extra=[]), lambda a: a["answers"].pop("route"),
                     lambda a: a["answers"].update(route=["invented"]), lambda a: a["answers"].update(route=["bus", "bus"]),
                     lambda a: a["answers"].update(unknowns=["invented"]), lambda a: a["answers"]["leave-by"].update(value=True)]
        for mutate in mutations:
            self.answer = response()
            mutate(self.answer)
            with self.assertRaises(evaluation.InputError):
                self.score()

    def test_case_contract_rejects_duplicate_ids_unknown_checks_and_shapes(self):
        mutations = [lambda c: c["rules"].append(copy.deepcopy(c["rules"][0])), lambda c: c["rules"][0].update(kind="unsupported"),
                     lambda c: c["facts"]["walk"].update(unit=[]), lambda c: c["facts"]["west-access"].update(value=True),
                     lambda c: c["rules"][0].update(minimum=True), lambda c: c["rules"][0]["options"].append(copy.deepcopy(c["rules"][0]["options"][0])),
                     lambda c: c["rules"][0]["options"][0].update(requires=[{"fact": "unknown", "equals": True}])]
        for mutate in mutations:
            self.case = fixture()
            mutate(self.case)
            with self.assertRaises(evaluation.InputError):
                self.score()

    def test_loader_rejects_ambiguous_unbounded_and_nonregular_inputs(self):
        path = self.root / "case.json"
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e9999}', b'\xff',
                    b'{"a":' + b'9' * 5000 + b'}', b'[' * 1100 + b'0' + b']' * 1100,
                    b'{"a":1.0000000000000001}', b'{"a":1e-20}',
                    b'{"a":0e9999999999999999999999999999}', b'{"a":0e-9999999999999999999999999999}',
                    b'"' + b'x' * (evaluation.MAX_BYTES + 1) + b'"', b'"\\ud800"'):
            path.write_bytes(raw)
            with self.assertRaises(evaluation.InputError):
                evaluation.load(path)
        link = self.root / "link.json"
        link.symlink_to(path)
        for bad in (link, self.root, self.root / "missing"):
            with self.assertRaises(evaluation.InputError):
                evaluation.load(bad)

    def test_cli_evaluates_exact_bytes_without_mutation_and_hides_oracles(self):
        case_path, answer_path = self.root / "case.json", self.root / "answer.json"
        self.case["examples"] = [{"id": "synthetic-oracle", "answers": self.answer["answers"], "expect": "pass"}]
        raw = json.dumps(self.case).encode()
        case_path.write_bytes(raw)
        self.answer["case_sha256"] = hashlib.sha256(raw).hexdigest()
        answer_path.write_text(json.dumps(self.answer))
        before = answer_path.read_bytes()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(evaluation.main(["--case", str(case_path), "--show-case"]), 0)
        shown = json.loads(output.getvalue())
        self.assertNotIn("rules", shown)
        self.assertNotIn("examples", shown)
        self.assertNotIn("synthetic-oracle", output.getvalue())
        contract = {field["id"]: field for field in shown["answer_fields"]}
        self.assertEqual(contract["route"]["allowed_ids"], ["east", "west", "bus"])
        self.assertEqual(contract["route"]["minimum"], 1)
        self.assertEqual(contract["unknowns"]["allowed_ids"], ["east-access", "west-access", "bus-access"])
        self.assertEqual(contract["leave-by"]["unit"], "minutes")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(evaluation.main(["--case", str(case_path), "--candidate", str(answer_path)]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["scope"], "synthetic_decision_fields")
        self.assertEqual(report["candidate_sha256"], hashlib.sha256(before).hexdigest())
        self.assertNotIn(str(self.root), output.getvalue())
        self.assertEqual(case_path.read_bytes(), raw)
        self.assertEqual(answer_path.read_bytes(), before)
        self.assertEqual(len(list(self.root.iterdir())), 2)

    def test_cli_invalid_inputs_have_categorical_pathless_diagnostics(self):
        case_path, answer_path = self.root / "case.json", self.root / "SYNTHETIC-PRIVATE.json"
        case_path.write_text(json.dumps(self.case))
        answer_path.write_text('{"SYNTHETIC-PRIVATE": NaN}')
        for path, expected in ((case_path, "invalid_candidate"), (answer_path, "invalid_case")):
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                self.assertEqual(evaluation.main(["--case", str(path), "--candidate", str(answer_path)]), 2)
            self.assertEqual(json.loads(output.getvalue()), {"result": expected})
            self.assertEqual(errors.getvalue(), "")

    def test_argument_errors_do_not_echo_paths_or_values(self):
        for arguments in (["--case", "SYNTHETIC-PRIVATE", "--show-case", "--unexpected", "SYNTHETIC-PRIVATE"],
                          ["--case"], ["--candidate", "SYNTHETIC-PRIVATE"],
                          ["--case", "SYNTHETIC-PRIVATE", "--candidate", "SYNTHETIC-PRIVATE", "--show-case"]):
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                self.assertEqual(evaluation.main(arguments), 2)
            self.assertEqual(json.loads(output.getvalue()), {"result": "invalid_arguments"})
            self.assertEqual(errors.getvalue(), "")

    def test_decimal_domain_is_exact_and_independent_of_global_context(self):
        facts = {"large": fact(1000000000, "AUD"), "small": fact(0.000001, "AUD"), "negative": fact(-1000000000, "AUD")}
        expression = {"op": "sum", "args": [{"fact": key} for key in facts]}
        with decimal.localcontext() as context:
            context.prec = 6
            self.assertEqual(evaluation.expression(expression, facts), (decimal.Decimal("0.000001"), "AUD"))
        facts["small"]["value"] = 1e-20
        with self.assertRaises(evaluation.InputError):
            evaluation.expression(expression, facts)
        too_precise = {"op": "scale", "factor": 0.000001, "arg": {"fact": "small"}}
        facts["small"]["value"] = 0.000001
        with self.assertRaises(evaluation.InputError):
            evaluation.expression(too_precise, facts)

    def test_installed_synthetic_examples(self):
        # Cases are optional installable resources; each installed case must exercise both outcomes.
        ids = set()
        for path in sorted((SKILL / "references/evaluation-cases").glob("*/*.json")):
            with self.subTest(case=path.name):
                case, digest = evaluation.load(path)
                evaluation.validate_case(case)
                self.assertNotIn(case["id"], ids)
                ids.add(case["id"])
                self.assertEqual({example["expect"] for example in case["examples"]}, {"pass", "fail"})
                for example in case["examples"]:
                    candidate = {"schema": "planning-answer/v1", "case_id": case["id"], "case_sha256": digest,
                                 "answers": example["answers"]}
                    with self.subTest(example=example["id"]):
                        self.assertEqual(evaluation.evaluate(case, candidate, digest)["result"], example["expect"])


if __name__ == "__main__":
    unittest.main()
