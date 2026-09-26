from __future__ import annotations

import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1] / "skills/travel-planning"
SPEC = importlib.util.spec_from_file_location("share_summary", SKILL / "scripts/export_share_summary.py")
share = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(share)


class Elements(HTMLParser):
    def __init__(self, document):
        super().__init__()
        self.tags = []
        self.feed(document)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class ShareSummaryTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((SKILL / "assets/example-itinerary.json").read_text())
        self.selection = {"schema_version": "travel-share-selection/v1", "attractions": [{"id": "a1", "public_label": "Lakeside walking"}]}

    def test_only_explicit_public_labels_cross_the_boundary(self):
        # Seed sensitive fields across the whole private data tree, including source names.
        marker = "SYNTHETIC-PRIVATE-MARKER"
        self.data["trip"].update(title=marker, travelers=marker, date_range=marker, contact=marker)
        for item in self.data["planning"]["attractions"]:
            item.update(name=marker, physical_address=marker, private_notes=marker)
        self.data["planning"]["lodging_options"] = [{"id": "private-hotel", "name": marker, "booking_reference": marker}]
        self.data["sources"] = [{"url": "https://example.test/?secret=" + marker, "title": marker}]
        self.data["private_extension"] = {"passport": marker, "medical": marker}
        self.data["days"][0]["events"][0].update(title=marker, notes=marker)
        before = copy.deepcopy(self.data)
        result = share.build(self.data, self.selection)
        self.assertIn("Lakeside walking", result)
        self.assertNotIn(marker, result)
        self.assertNotIn("2026-10-17", result)
        self.assertNotIn("a1", result)
        self.assertEqual(self.data, before)
        self.assertEqual(share.project(self.data, self.selection), {"title": "Travel highlights", "labels": ["Lakeside walking"]})

    def test_export_contains_no_scripts_links_or_automatic_resources(self):
        document = Elements(share.build(self.data, self.selection))
        for tag, attrs in document.tags:
            self.assertNotIn(tag, {"a", "img", "iframe", "script", "link", "object", "embed", "form"})
            self.assertFalse(set(attrs) & {"src", "srcset", "href", "ping", "action"})
        self.assertTrue(any(tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy" for tag, attrs in document.tags))

    def test_public_labels_are_escaped_and_not_interpreted_as_markup(self):
        self.selection["public_title"] = 'Walk <script> & "picnic"'
        self.selection["attractions"][0]["public_label"] = '<img src="https://example.test">'
        result = share.build(self.data, self.selection)
        self.assertIn("&lt;script&gt;", result)
        self.assertNotIn("<img", result)
        self.assertEqual(share.project(self.data, self.selection)["title"], self.selection["public_title"])

    def test_original_order_dates_and_ids_are_not_copied(self):
        self.selection["attractions"] = [{"id": "a2", "public_label": "Tea village"}, {"id": "a1", "public_label": "Lake"}]
        result = share.build(self.data, self.selection)
        self.assertLess(result.index("Tea village"), result.index("Lake"))
        self.assertNotIn("2026-10", result)
        self.assertNotIn("09:00", result)

    def test_invalid_unicode_fails_without_traceback_or_output_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, selection, output = (root / name for name in ("input.json", "selection.json", "public.html"))
            source.write_text(json.dumps(self.data), encoding="utf-8")
            output.write_text("previous", encoding="utf-8")
            for field in ("public_title", "public_label"):
                for surrogate in ("\ud800", "\udfff"):
                    with self.subTest(field=field, codepoint=ord(surrogate)):
                        candidate = copy.deepcopy(self.selection)
                        target = candidate if field == "public_title" else candidate["attractions"][0]
                        target[field] = "SYNTHETIC-PRIVATE " + surrogate
                        selection.write_text(json.dumps(candidate), encoding="utf-8")
                        before = (source.read_bytes(), selection.read_bytes(), output.read_bytes())
                        errors = io.StringIO()
                        args = ["export_share_summary.py", str(source), str(output), "--selection", str(selection)]
                        with patch.object(sys, "argv", args), redirect_stderr(errors):
                            with self.assertRaises(SystemExit) as caught:
                                share.main()
                        self.assertEqual(caught.exception.code, 1)
                        self.assertEqual(errors.getvalue(), "Share export failed: Public labels must contain valid Unicode text\n")
                        self.assertEqual((source.read_bytes(), selection.read_bytes(), output.read_bytes()), before)
                        self.assertEqual(set(root.iterdir()), {source, selection, output})

    def test_unicode_labels_round_trip_through_cli_entrypoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, selection, output = (root / name for name in ("input.json", "selection.json", "public.html"))
            source.write_text(json.dumps(self.data), encoding="utf-8")
            self.selection["public_title"] = "湖边散步 🌅"
            self.selection["attractions"][0]["public_label"] = "Café 🌿"
            # JSON escapes an astral character as a valid surrogate pair; it must remain supported.
            selection.write_text(json.dumps(self.selection), encoding="utf-8")
            args = ["export_share_summary.py", str(source), str(output), "--selection", str(selection)]
            with patch.object(sys, "argv", args), redirect_stdout(io.StringIO()):
                share.main()
            document = output.read_text(encoding="utf-8")
            self.assertIn("湖边散步 🌅", document)
            self.assertIn("Café 🌿", document)

    def test_unknown_selection_fields_and_invalid_entities_fail(self):
        cases = [
            {**self.selection, "private_notes": "SYNTHETIC-PRIVATE"},
            {**self.selection, "attractions": [{"id": "missing", "public_label": "Synthetic"}]},
            {**self.selection, "attractions": [{"id": "a1", "public_label": "Synthetic", "url": "SYNTHETIC-PRIVATE"}]},
            {**self.selection, "attractions": self.selection["attractions"] * 2},
        ]
        for selection in cases:
            with self.subTest(selection=selection):
                with self.assertRaises(share.ShareExportError) as caught:
                    share.build(self.data, selection)
                self.assertNotIn("SYNTHETIC-PRIVATE", str(caught.exception))
        self.data["planning"]["attractions"].append({"id": "unused"})
        with self.assertRaises(share.ShareExportError):
            share.build(self.data, {**self.selection, "attractions": [{"id": "unused", "public_label": "Unused"}]})

    def test_empty_selection_is_minimal_and_does_not_copy_defaults(self):
        result = share.build(self.data, {"schema_version": "travel-share-selection/v1"})
        self.assertIn("Travel highlights", result)
        self.assertNotIn(self.data["trip"]["title"], result)
        self.assertNotIn(self.data["planning"]["attractions"][0]["name"], result)

    def test_export_preserves_sources_and_previous_output_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, selection, output = (root / name for name in ("input.json", "selection.json", "public.html"))
            source.write_text(json.dumps(self.data)); selection.write_text(json.dumps(self.selection)); output.write_text("previous")
            before = (source.read_bytes(), selection.read_bytes())
            with patch.object(share.os, "replace", side_effect=OSError("SYNTHETIC-PRIVATE")):
                with self.assertRaises(share.ShareExportError) as caught:
                    share.export(source, selection, output)
            self.assertEqual(str(caught.exception), "Cannot write the share summary")
            self.assertEqual(output.read_text(), "previous")
            self.assertEqual(set(root.iterdir()), {source, selection, output})
            share.export(source, selection, output)
            self.assertEqual((source.read_bytes(), selection.read_bytes()), before)
            self.assertEqual(output.read_text(), share.build(self.data, self.selection))
            with self.assertRaises(share.ShareExportError):
                share.export(source, selection, source)


if __name__ == "__main__":
    unittest.main()
