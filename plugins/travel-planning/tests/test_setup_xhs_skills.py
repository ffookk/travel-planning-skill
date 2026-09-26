from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import traceback
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch
from contextlib import ExitStack
from urllib.error import HTTPError, URLError


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills" / "xiaohongshu" / "scripts" / "setup.py"
SPEC = importlib.util.spec_from_file_location("setup_xhs_mcp", MODULE_PATH)
assert SPEC and SPEC.loader
setup_xhs_mcp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup_xhs_mcp)


class SetupXhsMcpTest(unittest.TestCase):
    def runtime_paths(self, root: Path) -> ExitStack:
        stack = ExitStack()
        for name, path in {
            "DATA_ROOT": root, "STATE_DIR": root,
            "COOKIE_FILE": root / "cookies.json", "PID_FILE": root / "service.pid",
            "LOG_FILE": root / "service.log",
        }.items():
            stack.enter_context(patch.object(setup_xhs_mcp, name, path))
        stack.enter_context(patch.object(setup_xhs_mcp, "_verify_binary", return_value=True))
        stack.enter_context(patch.object(setup_xhs_mcp, "_binary", return_value=root / "synthetic-binary"))
        stack.enter_context(patch.object(setup_xhs_mcp, "_health", return_value=False))
        stack.enter_context(patch.dict(os.environ, {
            "PATH": "/synthetic/bin", "HOME": str(root),
            "PRIVATE_ACCOUNT_TOKEN": "unrelated-secret", "VARIFLIGHT_API_KEY": "provider-secret",
        }, clear=True))
        return stack

    def test_start_keeps_private_logs_out_of_errors_and_minimizes_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            process = MagicMock(pid=12345, returncode=1)
            process.poll.return_value = 1
            def start_process(*args, **kwargs):
                kwargs["stdout"].write(b"Cookie: synthetic-session-secret\n")
                return process
            with self.runtime_paths(root), patch.object(setup_xhs_mcp.subprocess, "Popen", side_effect=start_process) as start:
                with self.assertRaises(setup_xhs_mcp.SetupError) as raised:
                    setup_xhs_mcp.start(Namespace(timeout=5))
                self.assertNotIn("synthetic-session-secret", str(raised.exception))
                self.assertEqual(start.call_args.kwargs["env"], {
                    "PATH": "/synthetic/bin", "HOME": str(root), "COOKIES_PATH": str(root / "cookies.json"),
                })
                self.assertEqual((root / "service.log").stat().st_mode & 0o777, 0o600)

    def test_login_redirects_output_and_minimizes_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.runtime_paths(root), patch.object(setup_xhs_mcp.subprocess, "run", return_value=MagicMock(returncode=0)) as run:
                result = setup_xhs_mcp.login(Namespace())
                self.assertEqual(result["status"], "login_completed")
                self.assertEqual(run.call_args.kwargs["env"], {
                    "PATH": "/synthetic/bin", "HOME": str(root), "COOKIES_PATH": str(root / "cookies.json"),
                })
                self.assertEqual(run.call_args.kwargs["stdout"].name, str(root / "service.log"))
                self.assertEqual(run.call_args.kwargs["stderr"], setup_xhs_mcp.subprocess.STDOUT)
                self.assertEqual((root / "service.log").stat().st_mode & 0o777, 0o600)

    def test_logs_do_not_read_or_return_raw_contents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "service.log"
            path.write_text("arbitrary private upstream text", encoding="utf-8")
            with patch.object(setup_xhs_mcp, "LOG_FILE", path), patch.object(Path, "read_text", side_effect=AssertionError("Raw log read")):
                result = setup_xhs_mcp.logs(Namespace(lines=20))
            self.assertEqual(result["status"], "withheld")
            self.assertEqual(result["lines"], [])

    def test_download_errors_withhold_upstream_text_and_exception_chains(self) -> None:
        for error in (HTTPError("https://example.test/private", 403, "synthetic-secret", {}, None), URLError("synthetic-secret")):
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as directory:
                with patch.object(setup_xhs_mcp, "urlopen", side_effect=error):
                    try:
                        setup_xhs_mcp._download("binary", "0" * 64, Path(directory) / "binary")
                    except setup_xhs_mcp.SetupError:
                        self.assertNotIn("synthetic-secret", traceback.format_exc())
                    else:
                        self.fail("Expected a categorized download failure")

    def test_standalone_module_adds_plugin_root_for_shared_runtime_helpers(self) -> None:
        plugin_root = str(MODULE_PATH.parents[3])
        with patch.object(sys, "path", [entry for entry in sys.path if entry != plugin_root]):
            spec = importlib.util.spec_from_file_location("standalone_xhs_setup", MODULE_PATH)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertIn(plugin_root, sys.path)
            self.assertEqual(module.process_environment({"PRIVATE_TOKEN": "value"}), {})

    def test_status_reports_verified_pinned_install(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pid_file = root / "service.pid"
            with (
                patch.object(setup_xhs_mcp, "PID_FILE", pid_file),
                patch.object(setup_xhs_mcp, "DATA_ROOT", root),
                patch.object(setup_xhs_mcp, "STATE_DIR", root),
                patch.object(setup_xhs_mcp, "COOKIE_FILE", root / "cookies.json"),
                patch.object(setup_xhs_mcp, "LOG_FILE", root / "service.log"),
                patch.object(setup_xhs_mcp, "_verify_binary", return_value=True),
                patch.object(setup_xhs_mcp, "_health", return_value=False),
            ):
                result = setup_xhs_mcp.status(Namespace())
        self.assertEqual(result["status"], "installed")
        self.assertEqual(result["provider"], "xpzouying/xiaohongshu-mcp")
        self.assertEqual(result["version"], "v2.5.0")
        self.assertEqual(result["commit"], setup_xhs_mcp.UPSTREAM_COMMIT)
        self.assertTrue(result["assets_verified"]["server"])
        self.assertFalse(result["service"]["healthy"])

    def test_download_rejects_digest_mismatch(self) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_: object) -> None:
                return None

            def read(self, _: int) -> bytes:
                if getattr(self, "done", False):
                    return b""
                self.done = True
                return b"unexpected"

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "binary"
            with patch.object(setup_xhs_mcp, "urlopen", return_value=Response()):
                with self.assertRaises(setup_xhs_mcp.SetupError):
                    setup_xhs_mcp._download("binary", "0" * 64, destination)
            self.assertFalse(destination.exists())
            self.assertFalse(destination.with_suffix(".download").exists())


if __name__ == "__main__":
    unittest.main()
