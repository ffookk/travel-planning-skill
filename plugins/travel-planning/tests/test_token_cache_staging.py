from __future__ import annotations

import ast
import json
import os
import stat
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "skills/travel-planning/scripts/research_sources.py"


def cache_functions(path):
    # Load the actual cache definitions without importing provider or configuration code.
    names = {"SourceError", "read_token_cache", "cache_xhs_tokens"}
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    definitions = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names]
    namespace = {"Any": Any, "Path": Path, "json": json, "os": os, "tempfile": tempfile,
                 "xhs_token_cache_path": lambda: path, "checked_at": lambda: "2028-01-01T00:00:00+00:00"}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace


@contextmanager
def creation_mask(value):
    original = os.umask(value)
    try:
        yield
    finally:
        os.umask(original)


class TokenCacheStagingTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.cache = self.root / "state/tokens.json"
        self.cache.parent.mkdir()
        self.original = {"version": 1, "notes": {"old": {"xsec_token": "SYNTHETIC-OLD"}}, "extension": "retained"}
        self.cache.write_text(json.dumps(self.original), encoding="utf-8")
        self.functions = cache_functions(self.cache)
        self.feeds = [{"id": "new", "xsecToken": "SYNTHETIC-NEW", "sourceUrl": "https://example.test/note"}]

    def save(self, feeds=None, query="Synthetic query"):
        self.functions["cache_xhs_tokens"](self.feeds if feeds is None else feeds, query)

    def test_success_preserves_existing_fields_and_records_exact_feed_data(self):
        self.save()
        data = json.loads(self.cache.read_text(encoding="utf-8"))
        self.assertEqual(data["notes"]["old"], self.original["notes"]["old"])
        self.assertEqual(data["extension"], "retained")
        self.assertEqual(data["notes"]["new"], {"xsec_token": "SYNTHETIC-NEW", "source_url": "https://example.test/note", "query": "Synthetic query", "captured_at": "2028-01-01T00:00:00+00:00"})
        self.assertEqual(list(self.cache.parent.iterdir()), [self.cache])

    @unittest.skipUnless(os.name == "posix", "POSIX mode assertions")
    def test_staging_is_private_before_content_under_permissive_umasks(self):
        original_open = tempfile.NamedTemporaryFile
        observed = []
        def inspect_open(*args, **kwargs):
            stream = original_open(*args, **kwargs)
            observed.append((stat.S_IMODE(os.fstat(stream.fileno()).st_mode), os.fstat(stream.fileno()).st_size))
            return stream
        for mask in (0o022, 0o000):
            with self.subTest(mask=mask), creation_mask(mask), patch.object(tempfile, "NamedTemporaryFile", side_effect=inspect_open):
                self.cache.chmod(0o664)
                self.save()
                self.assertEqual(stat.S_IMODE(self.cache.stat().st_mode), 0o600)
        self.assertEqual(observed, [(0o600, 0), (0o600, 0)])

    def test_predictable_staging_symlink_is_never_followed_or_published(self):
        unrelated = self.root / "unrelated.txt"
        unrelated.write_bytes(b"Unrelated synthetic document")
        stale = self.cache.with_suffix(".json.tmp")
        stale.symlink_to(unrelated)
        self.save()
        self.assertEqual(unrelated.read_bytes(), b"Unrelated synthetic document")
        self.assertTrue(stale.is_symlink())
        self.assertFalse(self.cache.is_symlink())
        self.assertIn("new", json.loads(self.cache.read_text())["notes"])

    def test_interleaved_writes_do_not_consume_each_others_staging_file(self):
        replace = os.replace
        staged = []
        entered = False
        def interleave(source, target):
            nonlocal entered
            staged.append(Path(source))
            if not entered:
                entered = True
                self.save([{"id": "second", "xsecToken": "SYNTHETIC-SECOND"}])
            return replace(source, target)
        with patch.object(os, "replace", side_effect=interleave):
            self.save()
        self.assertEqual(len(set(staged)), 2)
        self.assertTrue(all(not path.exists() for path in staged))
        # The last complete replacement wins; this test does not promise merged concurrent updates.
        self.assertIn("new", json.loads(self.cache.read_text())["notes"])

    def test_write_sync_and_replace_failures_preserve_cache_and_clean_staging(self):
        before = self.cache.read_bytes()
        for operation in ("encoding", "fsync", "replace"):
            with self.subTest(operation=operation):
                if operation == "encoding":
                    with self.assertRaises(self.functions["SourceError"]):
                        self.save(query="Synthetic invalid text \ud800")
                else:
                    with patch.object(os, operation, side_effect=OSError("SYNTHETIC-PRIVATE-FAILURE")):
                        with self.assertRaises(self.functions["SourceError"]) as caught:
                            self.save()
                        self.assertNotIn("SYNTHETIC-PRIVATE-FAILURE", str(caught.exception))
                        self.assertTrue(caught.exception.__suppress_context__)
                self.assertEqual(self.cache.read_bytes(), before)
                self.assertEqual(list(self.cache.parent.iterdir()), [self.cache])

    def test_failed_first_update_leaves_no_cache_or_staging_file(self):
        self.cache.unlink()
        with patch.object(os, "replace", side_effect=OSError("Synthetic failure")):
            with self.assertRaises(self.functions["SourceError"]):
                self.save()
        self.assertEqual(list(self.cache.parent.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
