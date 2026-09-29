from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "skills/travel-planning/scripts/research_workspace.py"
SPEC = importlib.util.spec_from_file_location("archive_consistency_workspace", SOURCE)
workspace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workspace)


class ArchiveConsistencyTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.trip = self.root / "trip"
        workspace.write_json(self.trip / "manifest.json", {"workspace_version": 1})
        self.source = self.root / "synthetic-notice.txt"
        self.source.write_bytes(b"Synthetic source document")
        self.record = self.trip / "evidence/main/notice.json"
        self.stored = self.trip / "evidence/main/files/notice.txt"
        self.args = Namespace(workspace=str(self.trip), record_id="notice", task_id="main", kind="document",
                              title="Synthetic notice", url="https://example.test/notice", file=str(self.source),
                              source_kind="official", summary="Synthetic summary", query=None, location=None,
                              topic=None, tag=[], checked_at="2028-01-01T00:00:00+00:00", valid_until=None, freshness="stable")

    def assert_no_new_archive(self):
        self.assertFalse(self.record.exists())
        self.assertFalse(self.stored.exists())
        self.assertEqual(list((self.trip / "evidence").rglob(".*")), [])

    def test_record_describes_exact_staged_bytes_when_original_changes(self):
        original = self.source.read_bytes()
        replace = os.replace
        def change_original_before_publication(source, target):
            if Path(target) == self.stored:
                self.source.write_bytes(b"Later source version of another length")
            return replace(source, target)
        with patch.object(workspace.os, "replace", side_effect=change_original_before_publication):
            result = workspace.archive(self.args)
        record = result["record"]
        self.assertEqual(self.stored.read_bytes(), original)
        self.assertEqual(record["bytes"], len(original))
        self.assertEqual(record["sha256"], hashlib.sha256(self.stored.read_bytes()).hexdigest())
        self.assertNotEqual(record["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(record["checked_at"], self.args.checked_at)
        self.assertEqual(json.loads(self.record.read_bytes()), record)
        if os.name == "posix":
            self.assertEqual(self.stored.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.record.stat().st_mode & 0o777, 0o600)

    def test_source_is_opened_once_and_read_in_bounded_chunks(self):
        original_open = Path.open
        reads = []
        class Reader:
            def __init__(self, stream):
                self.stream = stream
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.stream.close()
            def read(self, count):
                reads.append(count)
                return self.stream.read(count)
        opened = []
        def inspect_open(path, *args, **kwargs):
            stream = original_open(path, *args, **kwargs)
            if path == self.source:
                opened.append(args[0])
                return Reader(stream)
            return stream
        with patch.object(Path, "open", new=inspect_open):
            workspace.archive(self.args)
        self.assertEqual(opened, ["rb"])
        self.assertTrue(reads)
        self.assertTrue(all(0 < count <= 1024 * 1024 for count in reads))

    def test_size_limit_is_enforced_on_streamed_bytes_and_boundary_is_allowed(self):
        self.source.write_bytes(b"123456789")
        with patch.object(workspace, "MAX_DOCUMENT_BYTES", 8):
            with self.assertRaisesRegex(workspace.WorkspaceError, "25 MiB"):
                workspace.archive(self.args)
            self.assert_no_new_archive()
            self.source.write_bytes(b"12345678")
            record = workspace.archive(self.args)["record"]
        self.assertEqual(record["bytes"], 8)
        self.assertEqual(self.stored.read_bytes(), b"12345678")

    def test_empty_document_remains_supported(self):
        self.source.write_bytes(b"")
        record = workspace.archive(self.args)["record"]
        self.assertEqual(record["bytes"], 0)
        self.assertEqual(record["sha256"], hashlib.sha256(b"").hexdigest())

    def test_record_replacement_failure_rolls_back_document_and_allows_retry(self):
        original = self.source.read_bytes()
        replace = os.replace
        def fail_record(source, target):
            if Path(target) == self.record:
                raise OSError("SYNTHETIC-PRIVATE-FAILURE")
            return replace(source, target)
        with patch.object(workspace.os, "replace", side_effect=fail_record):
            with self.assertRaises(workspace.WorkspaceError) as raised:
                workspace.archive(self.args)
        self.assertNotIn("SYNTHETIC-PRIVATE-FAILURE", str(raised.exception))
        self.assert_no_new_archive()
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(workspace.archive(self.args)["status"], "archived")

    def test_failed_metadata_encoding_does_not_leave_an_orphan(self):
        self.args.title = "Synthetic invalid title \ud800"
        with self.assertRaises(workspace.WorkspaceError):
            workspace.archive(self.args)
        self.assert_no_new_archive()
        self.args.title = "Synthetic valid title"
        self.assertEqual(workspace.archive(self.args)["status"], "archived")

    def test_document_sync_or_publication_failure_cleans_staging(self):
        for operation in ("fsync", "replace"):
            with self.subTest(operation=operation):
                with patch.object(workspace.os, operation, side_effect=OSError("Synthetic write failure")):
                    with self.assertRaises(workspace.WorkspaceError):
                        workspace.archive(self.args)
                self.assert_no_new_archive()

    def test_existing_record_and_copy_are_never_replaced(self):
        workspace.archive(self.args)
        before = (self.record.read_bytes(), self.stored.read_bytes())
        self.source.write_bytes(b"Different replacement attempt")
        with self.assertRaises(workspace.WorkspaceError):
            workspace.archive(self.args)
        self.assertEqual((self.record.read_bytes(), self.stored.read_bytes()), before)

    def test_existing_unrecorded_document_is_preserved_for_local_recovery(self):
        self.stored.parent.mkdir(parents=True)
        self.stored.write_bytes(b"Previous unrecorded copy")
        with self.assertRaises(workspace.WorkspaceError):
            workspace.archive(self.args)
        self.assertEqual(self.stored.read_bytes(), b"Previous unrecorded copy")
        self.assertFalse(self.record.exists())

    def test_failed_rollback_is_reported_without_echoing_private_details(self):
        unlink = Path.unlink
        def fail_copy_cleanup(path, *args, **kwargs):
            if path == self.stored:
                raise OSError("SYNTHETIC-PRIVATE-CLEANUP")
            return unlink(path, *args, **kwargs)
        with patch.object(workspace, "write_json", side_effect=OSError("SYNTHETIC-PRIVATE-WRITE")), patch.object(Path, "unlink", new=fail_copy_cleanup):
            with self.assertRaisesRegex(workspace.WorkspaceError, "could not be removed") as raised:
                workspace.archive(self.args)
        self.assertNotIn("SYNTHETIC-PRIVATE", str(raised.exception))
        self.assertTrue(self.stored.exists())
        self.assertFalse(self.record.exists())


if __name__ == "__main__":
    unittest.main()
