from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "skills/travel-planning/scripts/list_planning_guides.py"
SPEC = importlib.util.spec_from_file_location("planning_guide_catalog", SOURCE)
catalog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(catalog)


class PlanningGuideCatalogTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def add(self, slug="synthetic-guide", **changes):
        card = {"id": slug, "title": "Synthetic luggage transfer", "category": "transport",
                "when": "Use for a transfer with stored luggage", "tags": ["luggage", "行李寄存"]}
        card.update(changes)
        path = self.root / (slug + ".md")
        path.write_text(catalog.HEADER_PREFIX + json.dumps(card, ensure_ascii=False) + catalog.HEADER_SUFFIX + "\n\n# Synthetic body\n", encoding="utf-8")
        return path

    def test_missing_collection_and_no_match_return_empty(self):
        self.assertEqual(catalog.list_guides(self.root / "missing"), [])
        self.add()
        self.assertEqual(catalog.list_guides(self.root, query="unmatched"), [])

    def test_filtering_supports_casefold_multiple_terms_categories_and_chinese(self):
        self.add()
        self.add("synthetic-other", category="planning", title="Synthetic booking", when="Use for release timing", tags=["booking"])
        self.assertEqual(len(catalog.list_guides(self.root, query="LUGGAGE transfer", category="transport")), 1)
        self.assertEqual(len(catalog.list_guides(self.root, query="行李")), 1)
        self.assertEqual(catalog.list_guides(self.root, query="luggage booking"), [])
        self.assertEqual(catalog.list_guides(self.root, query="luggage", category="planning"), [])

    def test_cards_are_sorted_relative_and_do_not_include_bodies(self):
        self.add("synthetic-z")
        path = self.add("synthetic-a")
        with path.open("ab") as stream:
            stream.write(b"\xff" * 10000)
        before = path.read_bytes()
        results = catalog.list_guides(self.root)
        self.assertEqual([card["id"] for card in results], ["synthetic-a", "synthetic-z"])
        self.assertEqual(results[0]["path"], "references/scenarios/synthetic-a.md")
        self.assertNotIn(str(self.root), json.dumps(results))
        self.assertNotIn("Synthetic body", json.dumps(results))
        self.assertEqual(path.read_bytes(), before)

    def test_malformed_headers_fail_without_echoing_values_or_paths(self):
        path = self.add()
        cases = (
            (b"SYNTHETIC-PRIVATE\n", "Guide discovery metadata is missing"),
            (b"\xff\n", "Guide discovery metadata could not be read"),
            (b"x" * (catalog.MAX_HEADER_BYTES + 1), "Guide metadata exceeds the discovery size limit"),
            ((catalog.HEADER_PREFIX + '{"id":"a","id":"b"}' + catalog.HEADER_SUFFIX).encode(),
             "Guide metadata contains duplicate keys"),
            ((catalog.HEADER_PREFIX + '{"SYNTHETIC-PRIVATE":' + catalog.HEADER_SUFFIX).encode(),
             "Guide discovery metadata could not be read"),
        )
        for raw, expected in cases:
            with self.subTest(length=len(raw)):
                path.write_bytes(raw)
                with self.assertRaises(catalog.CatalogError) as caught:
                    catalog.list_guides(self.root)
                self.assertEqual(str(caught.exception), expected)
                self.assertNotIn("SYNTHETIC-PRIVATE", str(caught.exception))
                self.assertNotIn(str(self.root), str(caught.exception))
                errors = io.StringIO()
                with patch.object(catalog, "list_guides", side_effect=lambda **kwargs: [catalog.read_card(path)]), contextlib.redirect_stderr(errors):
                    self.assertEqual(catalog.main([]), 1)
                self.assertEqual(errors.getvalue(), expected + "\n")

    def test_filename_and_metadata_contract_reject_ambiguous_cards(self):
        for values in ({"id": "different"}, {"id": "../escape"}, {"title": ""}, {"category": "UPPER"},
                       {"when": "line\nbreak"}, {"tags": "scalar"}, {"tags": [None]}, {"tags": ["\ud800"]},
                       {"unexpected": True}):
            with self.subTest(values=values):
                path = self.root / "synthetic-guide.md"
                card = {"id": "synthetic-guide", "title": "Synthetic", "category": "planning", "when": "Synthetic", "tags": ["test"], **values}
                path.write_text(catalog.HEADER_PREFIX + json.dumps(card) + catalog.HEADER_SUFFIX, encoding="utf-8")
                with self.assertRaises(catalog.CatalogError):
                    catalog.list_guides(self.root)

    def test_numeric_and_nested_parser_limits_have_bounded_cli_errors(self):
        path = self.root / "synthetic-guide.md"
        payloads = ('{"value":' + '9' * 5000 + '}', '[' * 1500 + '0' + ']' * 1500)
        for payload in payloads:
            with self.subTest(length=len(payload)):
                path.write_text(catalog.HEADER_PREFIX + payload + catalog.HEADER_SUFFIX, encoding="utf-8")
                errors = io.StringIO()
                with patch.object(catalog, "list_guides", side_effect=lambda **kwargs: [catalog.read_card(path)]), contextlib.redirect_stderr(errors):
                    self.assertEqual(catalog.main([]), 1)
                self.assertNotIn(str(self.root), errors.getvalue())
                self.assertNotIn(payload, errors.getvalue())
                self.assertNotIn("Traceback", errors.getvalue())
                self.assertLess(len(errors.getvalue()), 100)

    def test_recursion_error_is_normalized_on_runtimes_with_other_parser_limits(self):
        path = self.add()
        with patch.object(catalog.json, "loads", side_effect=RecursionError("SYNTHETIC-PRIVATE")):
            with self.assertRaises(catalog.CatalogError) as caught:
                catalog.read_card(path)
        self.assertEqual(str(caught.exception), "Guide discovery metadata could not be read")
        self.assertTrue(caught.exception.__suppress_context__)

    def test_symlink_files_and_directories_are_rejected(self):
        target = self.add()
        link = self.root / "synthetic-link.md"
        link.symlink_to(target)
        with self.assertRaises(catalog.CatalogError):
            catalog.list_guides(self.root)
        link.unlink()
        folder_link = self.root / "linked"
        folder_link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(catalog.CatalogError):
            catalog.list_guides(folder_link)

    def test_nonregular_markdown_entries_are_rejected(self):
        path = self.root / "synthetic-directory.md"
        path.mkdir()
        with self.assertRaises(catalog.CatalogError) as caught:
            catalog.list_guides(self.root)
        self.assertEqual(str(caught.exception), "Guide references must be regular files")
        errors = io.StringIO()
        with patch.object(catalog, "list_guides", side_effect=lambda **kwargs: [catalog.read_card(path)]), contextlib.redirect_stderr(errors):
            self.assertEqual(catalog.main([]), 1)
        self.assertEqual(errors.getvalue(), "Guide references must be regular files\n")

    def test_cli_emits_machine_readable_cards_and_bounded_errors(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(catalog, "list_guides", return_value=[]) as listing, contextlib.redirect_stdout(output):
            self.assertEqual(catalog.main(["--query", "luggage", "--category", "transport"]), 0)
        listing.assert_called_once_with(query="luggage", category="transport")
        self.assertEqual(json.loads(output.getvalue()), {"guides": []})
        with patch.object(catalog, "list_guides", side_effect=catalog.CatalogError("Invalid guide")), contextlib.redirect_stderr(errors):
            self.assertEqual(catalog.main([]), 1)
        self.assertEqual(errors.getvalue(), "Invalid guide\n")


if __name__ == "__main__":
    unittest.main()
