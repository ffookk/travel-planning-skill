from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import stat
import tempfile
import unittest
from contextlib import ExitStack, contextmanager, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "travel-planning" / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location("artifact_test_" + name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


artifact_io = load("artifact_io")
renderer = load("render_itinerary")
assembler = load("assemble_itinerary")
auditor = load("audit_itinerary")


@contextmanager
def masked_creation(mask):
    previous = os.umask(mask)
    try:
        yield
    finally:
        os.umask(previous)


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        instant = cls(2028, 1, 1, 12, tzinfo=timezone.utc)
        return instant.astimezone(tz) if tz is not None else instant


@unittest.skipUnless(os.name == "posix", "Owner-only mode assertions require POSIX permissions")
class ArtifactIOTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = {
            "trip": {"title": "SYNTHETIC-PRIVATE-TRIP"},
            "days": [{"date": "2028-01-01", "events": [{
                "id": "synthetic-event", "type": "rest", "title": "Synthetic rest",
                "time": "09:00", "end_time": "10:00",
            }]}],
        }
        self.source = self.root / "input.json"
        self.source.write_text(json.dumps(self.data), encoding="utf-8")
        self.workspace = self.root / "workspace"
        for name in ("state", "sources", "results", "artifacts"):
            (self.workspace / name).mkdir(parents=True)
        research = self.workspace / "state" / "research.json"
        research.write_text(json.dumps({"schema_version": "travel-research-state/v2", "tasks": []}), encoding="utf-8")
        (self.workspace / "selected-route.json").write_text('{"id":"synthetic-route"}', encoding="utf-8")
        self.plan_path = self.workspace / "state" / "itinerary-plan.json"
        self.plan_path.write_text(json.dumps({
            "schema_version": "itinerary-plan/v1",
            "research_state_sha256": hashlib.sha256(research.read_bytes()).hexdigest(),
            "trip": self.data["trip"], "workflow": {"selected_route_id": "synthetic-route"},
            "collections": {}, "days": self.data["days"],
        }), encoding="utf-8")
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        self.patches.enter_context(patch.object(auditor, "datetime", FixedDatetime))
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.getaddrinfo", "subprocess.Popen"):
            self.patches.enter_context(patch(target, side_effect=AssertionError("Unexpected external operation")))

    def cases(self):
        return (
            ("html", renderer, lambda output: [self.source, output], renderer.build(self.data)),
            ("offline", renderer, lambda output: [self.source, output, "--private-offline"], renderer.build(self.data, private_offline=True)),
            ("assembly", assembler, lambda output: ["--workspace", self.workspace, "--output", output],
             json.dumps(assembler.assemble(self.workspace, self.plan_path), ensure_ascii=False, indent=2) + "\n"),
            ("audit", auditor, lambda output: [self.source, "--output", output],
             json.dumps(auditor.audit(self.data), ensure_ascii=False, indent=2) + "\n"),
        )

    def run_cli(self, module, arguments):
        with patch("sys.argv", [module.__name__, *map(str, arguments)]), redirect_stdout(io.StringIO()):
            try:
                module.main()
            except SystemExit as error:
                self.assertEqual(error.code, 0)

    def mode(self, path):
        return stat.S_IMODE(path.stat().st_mode)

    def test_all_cli_outputs_preserve_content_and_use_private_modes(self):
        inputs_before = (self.source.read_bytes(), self.plan_path.read_bytes())
        for mask in (0o022, 0o000):
            for name, module, arguments, expected in self.cases():
                with self.subTest(mask=oct(mask), command=name), masked_creation(mask):
                    output = self.root / f"{name}-{mask}.out"
                    self.run_cli(module, arguments(output))
                    self.assertEqual(output.read_bytes(), expected.encode("utf-8"))
                    self.assertEqual(self.mode(output), 0o600)
                    output.write_text("previous content", encoding="utf-8")
                    output.chmod(0o664)
                    self.run_cli(module, arguments(output))
                    self.assertEqual(output.read_bytes(), expected.encode("utf-8"))
                    self.assertEqual(self.mode(output), 0o600)
        self.assertEqual((self.source.read_bytes(), self.plan_path.read_bytes()), inputs_before)

    def test_default_assembly_output_is_also_private(self):
        with masked_creation(0o000):
            self.run_cli(assembler, ["--workspace", self.workspace])
        output = self.workspace / "artifacts" / "itinerary.json"
        self.assertEqual(self.mode(output), 0o600)
        self.assertEqual(json.loads(output.read_bytes()), assembler.assemble(self.workspace, self.plan_path))

    def test_cli_replacement_failures_preserve_existing_outputs_and_clean_temporary_files(self):
        for name, module, arguments, _ in self.cases():
            with self.subTest(command=name):
                output = self.root / f"failed-{name}.out"
                output.write_bytes(b"previous artifact")
                output.chmod(0o640)
                before = set(self.root.iterdir())
                with patch.object(module.artifact_io.os, "replace", side_effect=OSError("Synthetic replacement failure")):
                    with self.assertRaises(OSError):
                        self.run_cli(module, arguments(output))
                self.assertEqual(output.read_bytes(), b"previous artifact")
                self.assertEqual(self.mode(output), 0o640)
                self.assertEqual(set(self.root.iterdir()), before)

    def test_cli_outputs_refuse_symlinks_and_directories(self):
        victim = self.root / "synthetic-other-file"
        victim.write_bytes(b"unrelated content")
        for name, module, arguments, _ in self.cases():
            for kind in ("symlink", "directory"):
                with self.subTest(command=name, kind=kind):
                    output = self.root / f"{name}-{kind}"
                    if kind == "symlink":
                        output.symlink_to(victim)
                    else:
                        output.mkdir()
                    with self.assertRaisesRegex(OSError, "regular file"):
                        self.run_cli(module, arguments(output))
                    self.assertEqual(victim.read_bytes(), b"unrelated content")
                    self.assertEqual(list(self.root.glob(".travel-artifact-*")), [])

    def test_temporary_file_is_private_before_writing_without_chmod_of_parent(self):
        parent = self.root / "existing-shared-directory"
        parent.mkdir()
        parent.chmod(0o755)
        output = parent / "private.txt"
        fdopen = artifact_io.os.fdopen
        observed = []

        def inspect_open(descriptor, *args, **kwargs):
            observed.append(stat.S_IMODE(os.fstat(descriptor).st_mode))
            self.assertEqual(os.fstat(descriptor).st_size, 0)
            return fdopen(descriptor, *args, **kwargs)

        with masked_creation(0o000), patch.object(artifact_io.os, "fdopen", side_effect=inspect_open):
            artifact_io.write_private_text(output, "Synthetic private content\n")
        self.assertEqual(observed, [0o600])
        self.assertEqual(self.mode(parent), 0o755)
        self.assertEqual(self.mode(output), 0o600)

    def test_write_failures_preserve_previous_content_and_clean_staging(self):
        output = self.root / "private.txt"
        output.write_bytes(b"previous artifact")
        for failure in ("encoding", "flush"):
            with self.subTest(failure=failure):
                if failure == "encoding":
                    with self.assertRaises(UnicodeEncodeError):
                        artifact_io.write_private_text(output, "Synthetic invalid text: \ud800")
                else:
                    with patch.object(artifact_io.os, "fsync", side_effect=OSError("Synthetic flush failure")):
                        with self.assertRaises(OSError):
                            artifact_io.write_private_text(output, "Synthetic private content")
                self.assertEqual(output.read_bytes(), b"previous artifact")
                self.assertEqual(list(self.root.glob(".travel-artifact-*")), [])

    def test_failed_first_write_does_not_leave_an_output_or_staging_file(self):
        output = self.root / "new-private.txt"
        with patch.object(artifact_io.os, "replace", side_effect=OSError("Synthetic replacement failure")):
            with self.assertRaises(OSError):
                artifact_io.write_private_text(output, "Synthetic private content")
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.glob(".travel-artifact-*")), [])

    def test_umask_context_restores_process_state_after_failure(self):
        previous = os.umask(0o027)
        try:
            with self.assertRaisesRegex(RuntimeError, "Synthetic failure"):
                with masked_creation(0o000):
                    raise RuntimeError("Synthetic failure")
            observed = os.umask(0o027)
            self.assertEqual(observed, 0o027)
        finally:
            os.umask(previous)


if __name__ == "__main__":
    unittest.main()
