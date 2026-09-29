from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


SKILL = Path(__file__).resolve().parents[1] / "skills" / "travel-planning"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SKILL / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = load("verify_final_delivery")
finalizer = load("finalize_itinerary")


class ReceiptVerificationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.html = self.root / "private.html"
        self.receipt_path = self.root / "receipt.json"
        self.input = self.root / "input.json"
        self.research = self.root / "research.json"
        self.decisions = self.root / "decisions.json"
        self.html.write_bytes(b"<html>SYNTHETIC-PRIVATE</html>\n")
        self.input.write_bytes(b'{"synthetic":"PRIVATE"}\n')
        self.research.write_bytes(b'{"synthetic":"research"}\n')
        self.decisions.write_bytes(b'{"synthetic":"decisions"}\n')
        self.receipt = {
            "schema_version": "itinerary-final-delivery/v1", "status": "pass",
            "itinerary_sha256": self.sha(self.input), "html_sha256": self.sha(self.html),
            "research_sha256": None, "decisions_sha256": None, "export_profile": "regular",
            "checked_at": "2026-09-20T12:00:00+00:00", "warning_count": 1, "checked_event_count": 2,
            "conflicts": {"status": "conflicts_not_checked"},
        }
        self.write_receipt()

    def sha(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def write_receipt(self):
        binding = {key: self.receipt[key] for key in verifier.BINDING_FIELDS}
        self.receipt["binding_sha256"] = hashlib.sha256(verifier.canonical(binding)).hexdigest()
        self.receipt_path.write_text(json.dumps(self.receipt) + "\n", encoding="utf-8")

    def checked_research(self):
        self.receipt.update(research_sha256=self.sha(self.research), decisions_sha256=self.sha(self.decisions),
                            conflicts={"status": "checked", "resolved_conflict_count": 1, "unused_conflict_count": 0})
        self.write_receipt()

    def test_explicit_scope_distinguishes_missing_artifacts_from_unrecorded_ones(self):
        result = verifier.verify(self.html, self.receipt_path)
        self.assertEqual(result["checks"], {"html": "matched", "itinerary": "not_supplied", "research": "not_recorded", "decisions": "not_recorded"})
        self.assertEqual(result["authenticity"], "not_verified")
        self.assertEqual(result["source_freshness"], "not_checked")
        self.checked_research()
        result = verifier.verify(self.html, self.receipt_path, input_path=self.input)
        self.assertEqual(result["checks"], {"html": "matched", "itinerary": "matched", "research": "not_supplied", "decisions": "not_supplied"})
        result = verifier.verify(self.html, self.receipt_path, input_path=self.input, research_path=self.research, decisions_path=self.decisions)
        self.assertEqual(set(result["checks"].values()), {"matched"})

    def test_real_finalizer_receipt_verifies_after_copying_and_renaming(self):
        data = json.loads((SKILL / "assets" / "example-itinerary.json").read_bytes())
        data["workflow"]["phase"] = "final"
        self.input.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        finalizer.finalize(self.input, self.html, self.receipt_path)
        relocated = self.root / "copied"
        relocated.mkdir()
        copied = []
        for source, name in ((self.input, "renamed-input.json"), (self.html, "renamed.html"), (self.receipt_path, "renamed-receipt.json")):
            copied.append(relocated / name)
            shutil.copyfile(source, copied[-1])
            source.unlink()
        result = verifier.verify(copied[1], copied[2], input_path=copied[0], require_profile="regular")
        self.assertEqual(result["status"], "match")
        self.assertEqual(result["checks"]["itinerary"], "matched")

    def test_changed_artifact_bytes_are_rejected_without_rewriting_any_files(self):
        self.checked_research()
        paths = [(self.html, {}), (self.input, {"input_path": self.input}),
                 (self.research, {"research_path": self.research}), (self.decisions, {"decisions_path": self.decisions})]
        for path, arguments in paths:
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            before = {file: file.read_bytes() for file in self.root.iterdir()}
            with self.subTest(path=path.name), self.assertRaises(verifier.VerificationError):
                verifier.verify(self.html, self.receipt_path, **arguments)
            self.assertEqual({file: file.read_bytes() for file in self.root.iterdir()}, before)
            path.write_bytes(original)

    def test_required_profile_is_checked_against_receipt_declaration(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.verify(self.html, self.receipt_path, require_profile="private-offline")
        self.receipt["export_profile"] = "private-offline"
        self.write_receipt()
        self.assertEqual(verifier.verify(self.html, self.receipt_path, require_profile="private-offline")["export_profile"], "private-offline")

    def test_receipt_binding_changes_and_swapped_html_are_detected(self):
        self.receipt["binding_sha256"] = "0" * 64
        self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
        with self.assertRaises(verifier.VerificationError):
            verifier.verify(self.html, self.receipt_path)
        self.receipt["html_sha256"] = hashlib.sha256(b"a different delivery").hexdigest()
        self.write_receipt()
        with self.assertRaises(verifier.VerificationError):
            verifier.verify(self.html, self.receipt_path)

    def test_invalid_receipt_structure_and_metadata_fail_before_artifact_reads(self):
        mutations = [
            ("schema_version", "unknown"), ("status", "fail"), ("export_profile", []),
            ("html_sha256", "x" * 64), ("itinerary_sha256", None), ("research_sha256", 3),
            ("decisions_sha256", "f" * 64), ("checked_at", "2026-09-20"),
            ("warning_count", True), ("checked_event_count", -1), ("conflicts", {"status": "checked"}),
            ("unexpected_path", "SYNTHETIC-PRIVATE"),
        ]
        original = copy.deepcopy(self.receipt)
        for key, value in mutations:
            self.receipt = {**original, key: value}
            self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
            with self.subTest(key=key), patch.object(verifier, "file_digest") as read:
                with self.assertRaises(verifier.VerificationError):
                    verifier.verify(self.html, self.receipt_path)
                read.assert_not_called()
        self.receipt = original
        del self.receipt["html_sha256"]
        self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
        with self.assertRaises(verifier.VerificationError):
            verifier.verify(self.html, self.receipt_path)

    def test_duplicate_keys_nonfinite_invalid_encoding_and_oversized_receipts_fail(self):
        for raw in (b'{"status":"pass","status":"fail"}', b'{"value":NaN}', b'\xff',
                    b' ' * (verifier.MAX_RECEIPT_BYTES + 1), b'[]', b'not JSON'):
            with self.subTest(raw=raw[:30]):
                self.receipt_path.write_bytes(raw)
                with self.assertRaises(verifier.VerificationError):
                    verifier.verify(self.html, self.receipt_path)

    def test_unrecorded_optional_input_is_refused_without_reading_it(self):
        reads = []
        actual = verifier.file_digest
        def digest(path):
            reads.append(path)
            return actual(path)
        with patch.object(verifier, "file_digest", side_effect=digest):
            with self.assertRaises(verifier.VerificationError):
                verifier.verify(self.html, self.receipt_path, research_path=self.root / "never-read.json")
        self.assertEqual(reads, [self.html])

    def test_only_explicit_files_are_read_and_success_output_omits_paths_and_contents(self):
        before = {file: file.read_bytes() for file in self.root.iterdir()}
        actual_open = Path.open
        opened = []
        def explicit_open(path, *args, **kwargs):
            opened.append(path)
            self.assertIn(path, {self.html, self.receipt_path})
            return actual_open(path, *args, **kwargs)
        output = io.StringIO()
        with patch.object(Path, "open", explicit_open), patch("sys.argv", ["verify", str(self.html), str(self.receipt_path)]), redirect_stdout(output):
            self.assertEqual(verifier.main(), 0)
        self.assertEqual(set(opened), {self.html, self.receipt_path})
        self.assertNotIn(str(self.root), output.getvalue())
        self.assertNotIn("SYNTHETIC-PRIVATE", output.getvalue())
        self.assertEqual({file: file.read_bytes() for file in self.root.iterdir()}, before)

    def test_io_and_argument_failures_have_bounded_generic_diagnostics(self):
        cases = [(["verify", str(self.root / "SYNTHETIC-PRIVATE"), str(self.receipt_path)], 1),
                 (["verify", str(self.html), str(self.receipt_path), "--require-profile", "SYNTHETIC-PRIVATE"], 2)]
        for args, code in cases:
            errors = io.StringIO()
            with patch("sys.argv", args), redirect_stderr(errors):
                if code == 1:
                    self.assertEqual(verifier.main(), code)
                else:
                    with self.assertRaises(SystemExit) as caught:
                        verifier.main()
                    self.assertEqual(caught.exception.code, code)
            self.assertLess(len(errors.getvalue()), 200)
            self.assertNotIn(str(self.root), errors.getvalue())
            self.assertNotIn("SYNTHETIC-PRIVATE", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
