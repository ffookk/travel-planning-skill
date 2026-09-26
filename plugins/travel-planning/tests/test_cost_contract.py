from __future__ import annotations

import copy
import hashlib
import tempfile
import importlib.util
import json
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1] / "skills/travel-planning"

def load(name):
    spec = importlib.util.spec_from_file_location("cost_test_" + name, SKILL / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

assembler = load("assemble_itinerary")
auditor = load("audit_itinerary")


class CostContractTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((SKILL / "assets/example-itinerary.json").read_text())
        self.defaults = assembler.default_settings(self.data)

    def selected_quote(self, quote):
        edge = self.data["planning"]["transport_edges"][0]
        self.assertTrue(any(e.get("route_id") == edge["id"] for day in self.data["days"] for e in day["events"]))
        edge["cost"] = quote
        self.data["planning"]["transport_edges"][0] = assembler.normalize_route(edge, self.defaults)
        return auditor.audit(self.data)

    def test_assembly_keeps_structured_currency_and_does_not_rewrite_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("state", "results", "sources", "snapshots"):
                (root / name).mkdir()
            research = root / "state/research.json"
            research.write_text(json.dumps({"schema_version": "travel-research-state/v2", "tasks": []}))
            (root / "selected-route.json").write_text(json.dumps({"id": "chosen"}))
            result_path = root / "results/transport.json"
            quote = {"amount": 200, "currency": "AUD", "basis": "group", "traveler_count": 2}
            result_path.write_text(json.dumps({"task_id": "transport", "source_snapshot_ids": [], "entities": {"transport_edges": [{"id": "route", "cost": quote}]}}))
            plan = {"schema_version": "itinerary-plan/v1", "research_state_sha256": hashlib.sha256(research.read_bytes()).hexdigest(),
                    "trip": {"title": "Synthetic", "travelers": "2 adults"}, "workflow": {"selected_route_id": "chosen"},
                    "collections": {"transport_edges": {"task": "transport", "path": "entities.transport_edges", "ids": ["route"]}},
                    "days": [{"date": "2028-01-01", "events": [{"id": "event", "type": "transport", "route_id": "route", "time": "08:00", "end_time": "09:00"}]}]}
            plan_path = root / "state/plan.json"
            plan_path.write_text(json.dumps(plan))
            before = (result_path.read_bytes(), plan_path.read_bytes())
            assembled = assembler.assemble(root, plan_path)
            route = assembled["planning"]["transport_edges"][0]
            self.assertEqual(route["cost"], "AUD 200/组（适用 2 人）")
            self.assertEqual(route["cost_quote"], quote)
            self.assertEqual((result_path.read_bytes(), plan_path.read_bytes()), before)

    def test_public_example_still_passes(self):
        result = auditor.audit(self.data)
        self.assertEqual(result["status"], "pass")
        self.assertFalse(any("cost" in value.lower() or "traveler_count" in value for value in result["warnings"]))

    def test_group_foreign_currency_preserves_evidence_and_party(self):
        quote = {"amount": 200, "currency": "AUD", "basis": "group", "traveler_count": 2, "taxes": "included", "source_ids": ["fixture"]}
        original = copy.deepcopy(quote)
        result = self.selected_quote(quote)
        edge = self.data["planning"]["transport_edges"][0]
        self.assertEqual(result["status"], "pass")
        self.assertEqual(edge["cost"], "AUD 200/组（适用 2 人） · 含税费")
        self.assertEqual(edge["cost_quote"], original)
        self.assertEqual(quote, original)

    def test_legacy_currency_metadata_does_not_opt_in_to_generic_amounts(self):
        quote = {"amount_yuan_for_4": "400-500", "currency": "CNY", "basis": "group"}
        result = assembler.normalize_route({"cost": quote}, self.defaults)
        self.assertEqual(result["cost"], "4人约 400-500 元（估算）")
        self.assertEqual(result["cost_quote"], quote)
        intercity = assembler.normalize_intercity({"cost": {"amount_yuan_per_adult": 100, "currency": "CNY"}}, self.defaults)
        self.assertEqual(intercity["cost"], "约¥100/人（待复核）")

    def test_intercity_generic_price_and_supplied_display(self):
        quote = {"amount": 0, "currency": "EUR", "basis": "per_person", "display": "Included in pass", "taxes": "unknown"}
        result = assembler.normalize_intercity({"cost": quote}, self.defaults)
        self.assertEqual(result["cost"], "Included in pass")
        self.assertEqual(result["cost_quote"], quote)
        self.assertEqual(assembler.normalize_route({"cost": {**quote, "display": ""}}, self.defaults)["cost"], "EUR 0/人 · 税费待核")

    def test_legacy_four_person_quote_is_retained_but_mismatch_blocks(self):
        result = self.selected_quote({"amount_yuan_for_4": 400, "status": "estimated"})
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any("4 travelers but the trip has 2" in x for x in result["blocking"]))
        self.assertEqual(self.data["planning"]["transport_edges"][0]["cost"], "4人约 400 元（estimated）")
        self.data["trip"]["traveler_count"] = 4
        self.assertEqual(auditor.audit(self.data)["status"], "pass")

    def test_unselected_quote_does_not_block(self):
        unused = copy.deepcopy(self.data["planning"]["transport_edges"][0])
        unused.update(id="unused", cost={"amount_yuan_for_4": 400})
        self.data["planning"]["transport_edges"].append(assembler.normalize_route(unused, self.defaults))
        self.assertEqual(auditor.audit(self.data)["status"], "pass")

    def test_ambiguous_party_description_requires_explicit_count(self):
        self.data["trip"]["travelers"] = "Two adults and children; count pending"
        result = self.selected_quote({"amount": 300, "currency": "USD", "basis": "group", "traveler_count": 3})
        self.assertTrue(any("trip.traveler_count" in x for x in result["warnings"]))
        self.data["trip"]["traveler_count"] = 3
        self.assertFalse(any("trip.traveler_count" in x for x in auditor.audit(self.data)["warnings"]))

    def test_structured_line_item_estimate_is_exact_and_not_a_provider_total(self):
        item = {"name": "Synthetic ticket", "price": {"amount": "19.99", "currency": "USD", "basis": "per_person"}, "quantity": 3, "pricing_role": "baseline"}
        original = copy.deepcopy(item)
        result = assembler.normalize_cost(item)
        self.assertEqual(result["unit_price"], "USD 19.99/人")
        self.assertEqual(result["subtotal"], "USD 59.97（规划估算，非供应商总价）")
        self.assertEqual(result["price_evidence"], item["price"])
        self.assertEqual(item, original)

    def test_subtotal_display_is_preserved_and_quantity_is_not_guessed(self):
        item = {"price": {"amount": 12, "currency": "GBP", "basis": "per_item"}}
        result = assembler.normalize_cost(item)
        self.assertEqual(result["quantity"], "待核")
        self.assertEqual(result["subtotal"], "数量待核")
        item.update(quantity=2, subtotal="Provider package total: GBP 20 including fees")
        self.assertEqual(assembler.normalize_cost(item)["subtotal"], item["subtotal"])

    def test_currencies_are_separate_and_free_amount_remains_zero(self):
        outputs = [assembler.normalize_cost({"price": {"amount": value, "currency": currency, "basis": "per_item"}, "quantity": 2}) for value, currency in ((0, "JPY"), (10, "AUD"), (10, "USD"))]
        self.assertEqual([x["unit_price"] for x in outputs], ["JPY 0/项", "AUD 10/项", "USD 10/项"])
        self.assertTrue(outputs[0]["subtotal"].startswith("JPY 0"))

    def test_legacy_cost_display_is_unchanged(self):
        item = {"name": "Old ticket", "unit_price_cny": 0, "subtotal_cny": 0, "quantity": 1, "pricing_role": "baseline", "status": "free"}
        result = assembler.normalize_cost(item)
        self.assertEqual(result["unit_price"], "¥0")
        self.assertEqual(result["subtotal"], "¥0")
        self.assertNotIn("price_evidence", result)

    def test_invalid_structured_values_fail_without_echoing_payload(self):
        base = {"amount": 10, "currency": "AUD", "basis": "group"}
        for field, values in {
            "amount": [-1, True, float("nan"), "Infinity", "1e999999", "1e-1000100", "SYNTHETIC-PRIVATE"],
            "currency": [None, "aud", "SYNTHETIC-PRIVATE"],
            "basis": [[], "SYNTHETIC-PRIVATE"],
            "traveler_count": [True, 0, -1, "2"],
            "taxes": [[], "SYNTHETIC-PRIVATE"],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(assembler.AssemblyError) as caught:
                        assembler.normalize_route({"cost": {**base, field: value}}, self.defaults)
                    self.assertNotIn("SYNTHETIC-PRIVATE", str(caught.exception))

    def test_alternative_package_and_single_tickets_cannot_both_be_baseline(self):
        event = next(e for day in self.data["days"] for e in day["events"] if e.get("cost_items"))
        first = event["cost_items"][0]
        first.update(alternative_group="fixture-options", pricing_role="baseline")
        second = {**copy.deepcopy(first), "kind": "package"}
        event["cost_items"].append(second)
        self.assertTrue(any("same baseline group" in x for x in auditor.audit(self.data)["blocking"]))
        second["pricing_role"] = "alternative"
        self.assertFalse(any("same baseline group" in x for x in auditor.audit(self.data)["blocking"]))


if __name__ == "__main__":
    unittest.main()
