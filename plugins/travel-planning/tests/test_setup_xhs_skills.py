from __future__ import annotations

import importlib.util
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "skills" / "xiaohongshu" / "scripts" / "setup.py"
SPEC = importlib.util.spec_from_file_location("setup_xhs_skills", MODULE_PATH)
assert SPEC and SPEC.loader
setup_xhs_skills = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup_xhs_skills)


class SetupXhsSkillsTest(unittest.TestCase):
    def test_status_reports_pinned_ready_install(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            venv = Path(directory) / ".venv"
            venv.mkdir(parents=True)
            (venv / "pyvenv.cfg").write_text("home = test\n", encoding="utf-8")
            with patch.object(setup_xhs_skills, "VENV_DIR", venv):
                result = setup_xhs_skills.status(Namespace())
        self.assertEqual(result["status"], "installed")
        self.assertEqual(result["actual_commit"], setup_xhs_skills.UPSTREAM_COMMIT)
        self.assertTrue(result["dependencies_installed"])
        self.assertIsNone(result["live_query_available"])

    def test_upstream_skill_rejects_unpinned_install(self) -> None:
        with patch.object(setup_xhs_skills, "vendored_source_present", return_value=False):
            with self.assertRaises(setup_xhs_skills.SetupError):
                setup_xhs_skills.upstream_skill(Namespace())


if __name__ == "__main__":
    unittest.main()
