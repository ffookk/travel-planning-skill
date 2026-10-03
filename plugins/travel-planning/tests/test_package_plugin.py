from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGING_SCRIPT = REPOSITORY_ROOT / "scripts/package_plugin.py"
if not PACKAGING_SCRIPT.is_file():
    raise unittest.SkipTest("Packaging tests require the source checkout's scripts/package_plugin.py")
SPEC = importlib.util.spec_from_file_location(
    "package_plugin", PACKAGING_SCRIPT
)
assert SPEC and SPEC.loader
package_plugin = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package_plugin)


class PackagePluginTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / "repository"
        self.root.mkdir()
        self.plugin = Path("plugins/travel-planning")
        self.output = Path("output/package.zip")
        self.environment = dict(os.environ)
        self.environment.update({
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_COUNT": "0",
        })
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
            self.environment.pop(key, None)
        environment_patch = patch.dict(os.environ, self.environment, clear=True)
        environment_patch.start()
        self.addCleanup(environment_patch.stop)
        root_patch = patch.object(package_plugin, "REPOSITORY_ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.git("-c", "init.templateDir=", "init", "-q")
        self.write(Path("README.md"), "Public documentation")
        self.write(Path(".agents/plugins/marketplace.json"), "{}")
        self.write(self.plugin / ".codex-plugin/plugin.json", "{}")
        self.write(self.plugin / "config/sources.example.env", "FLYAI_API_KEY=\n")
        self.write(self.plugin / "skills/travel-planning/SKILL.md", "Public skill")
        self.write(Path(".gitignore"), "**/sources.local.env\n**/.travel-research/\noutput/\n")
        self.git("add", ".")

    def git(self, *arguments: str) -> None:
        subprocess.run(
            ["git", "-C", os.fspath(self.root), *arguments],
            check=True,
            capture_output=True,
        )

    def write(self, relative_path: Path, content: str = "synthetic fixture") -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def build(self) -> int:
        return package_plugin.build_archive(self.plugin, self.output, "bundle")

    def assert_refused(self, path: Path, reason: str = "private runtime path") -> None:
        with self.assertRaises(SystemExit) as raised:
            self.build()
        message = str(raised.exception)
        self.assertIn(path.as_posix(), message)
        self.assertIn(reason, message)
        self.assertNotIn(str(self.root), message)
        self.assertNotIn("SYNTHETIC-SECRET", message)

    def test_packages_tracked_and_untracked_public_resources(self) -> None:
        self.write(self.plugin / "references/new-guide.md", "Untracked public guide")
        self.write(self.plugin / "assets/frontend/app.js", "public frontend")
        self.write(self.plugin / "config/sources.local.env", "SYNTHETIC-SECRET")
        self.write(self.plugin / ".travel-research/trip/research.json", "SYNTHETIC-SECRET")
        self.write(Path("unrelated.txt"), "outside the package selection")

        count = self.build()
        with zipfile.ZipFile(self.root / self.output) as archive:
            names = set(archive.namelist())
            self.assertEqual(count, len(names))
            self.assertIn("bundle/README.md", names)
            self.assertIn("bundle/.agents/plugins/marketplace.json", names)
            self.assertIn("bundle/plugins/travel-planning/config/sources.example.env", names)
            self.assertIn("bundle/plugins/travel-planning/references/new-guide.md", names)
            self.assertIn("bundle/plugins/travel-planning/assets/frontend/app.js", names)
            self.assertFalse(any("sources.local.env" in name for name in names))
            self.assertFalse(any(".travel-research" in name for name in names))
            self.assertFalse(any("unrelated.txt" in name for name in names))

    def test_rejects_force_tracked_ignored_credentials_before_creating_archive(self) -> None:
        relative = self.plugin / "config/sources.local.env"
        self.write(relative, "SYNTHETIC-SECRET")
        self.git("add", "-f", relative.as_posix())
        self.assert_refused(relative)
        self.assertFalse((self.root / self.output).exists())
        self.assertFalse((self.root / self.output.parent).exists())

    def test_rejection_preserves_existing_archive(self) -> None:
        self.build()
        before = (self.root / self.output).read_bytes()
        relative = self.plugin / "config/sources.local.env"
        self.write(relative, "SYNTHETIC-SECRET")
        self.git("add", "-f", relative.as_posix())
        self.assert_refused(relative)
        self.assertEqual((self.root / self.output).read_bytes(), before)
        self.assertEqual(list((self.root / self.output.parent).iterdir()), [self.root / self.output])

    def test_rejects_tracked_private_runtime_paths(self) -> None:
        paths = (
            ".env", ".env.production", "config/provider.env", "config/provider.env.backup",
            ".travel-research/trip/notes.json", ".travel-tools/runtime/data.json",
            ".playwright-cli/page.png", "state/cookies.json", "state/cookies.txt",
            "state/search-tokens.json", "state/service.log", "state/service.pid",
            "state/service.log.1", "state/storage-state.json",
            ".cache/query.json", "__pycache__/module.pyc", "node_modules/pkg/data.json",
        )
        for name in paths:
            with self.subTest(path=name):
                relative = self.plugin / name
                path = self.write(relative, "SYNTHETIC-SECRET")
                self.git("add", "-f", relative.as_posix())
                self.assert_refused(relative)
                self.assertFalse((self.root / self.output).exists())
                self.git("rm", "--cached", "-f", relative.as_posix())
                path.unlink()

    def test_rejects_untracked_credentials_without_ignore_rule(self) -> None:
        relative = self.plugin / "config/provider.env"
        self.write(relative, "SYNTHETIC-SECRET")
        self.assert_refused(relative)
        self.assertFalse((self.root / self.output).exists())

    def test_preserves_relative_internal_symlink(self) -> None:
        relative = self.plugin / "public-guide.md"
        (self.root / relative).symlink_to("skills/travel-planning/SKILL.md")
        directory_relative = self.plugin / "public-skills"
        (self.root / directory_relative).symlink_to("skills", target_is_directory=True)
        self.build()
        with zipfile.ZipFile(self.root / self.output) as archive:
            name = f"bundle/{relative.as_posix()}"
            self.assertTrue(stat.S_ISLNK(archive.getinfo(name).external_attr >> 16))
            self.assertEqual(archive.read(name), b"skills/travel-planning/SKILL.md")
            self.assertEqual(archive.read(f"bundle/{directory_relative.as_posix()}"), b"skills")

    def test_rejects_external_symlink_without_replacing_existing_archive(self) -> None:
        self.build()
        before = (self.root / self.output).read_bytes()
        outside = self.root.parent / "outside.txt"
        outside.write_text("SYNTHETIC-SECRET", encoding="utf-8")
        relative = self.plugin / "public-guide.md"
        (self.root / relative).symlink_to("../../../outside.txt")
        self.assert_refused(relative, "symlink target leaves the repository")
        self.assertEqual((self.root / self.output).read_bytes(), before)

    def test_rejects_absolute_symlink_even_with_internal_target(self) -> None:
        relative = self.plugin / "public-guide.md"
        (self.root / relative).symlink_to(self.root / "README.md")
        self.assert_refused(relative, "absolute symlink target")
        self.assertFalse((self.root / self.output).exists())

    def test_rejects_symlink_to_ignored_private_target(self) -> None:
        self.write(self.plugin / "config/sources.local.env", "SYNTHETIC-SECRET")
        relative = self.plugin / "public-guide.md"
        (self.root / relative).symlink_to("config/sources.local.env")
        self.assert_refused(relative, "symlink target is a private runtime path")
        self.assertFalse((self.root / self.output).exists())

    def test_rejects_private_intermediate_symlink_target(self) -> None:
        private = self.root / self.plugin / ".travel-research"
        private.mkdir()
        (private / "alias").symlink_to("../skills")
        relative = self.plugin / "public-guide.md"
        (self.root / relative).symlink_to(".travel-research/alias/travel-planning/SKILL.md")
        self.assert_refused(relative, "symlink target is a private runtime path")

    def test_rejects_unselected_and_missing_symlink_targets(self) -> None:
        self.write(Path("unrelated.txt"), "not in the package")
        relative = self.plugin / "public-guide.md"
        link = self.root / relative
        link.symlink_to("../../unrelated.txt")
        self.assert_refused(relative, "symlink target is outside the package file set")
        link.unlink()
        link.symlink_to("missing.txt")
        self.assert_refused(relative, "symlink target does not exist")

    def test_rejects_cyclic_symlinks(self) -> None:
        relative = self.plugin / "public-guide.md"
        (self.root / relative).symlink_to("other-guide.md")
        (self.root / self.plugin / "other-guide.md").symlink_to("public-guide.md")
        with self.assertRaisesRegex(SystemExit, "symlink target is cyclic"):
            self.build()
        self.assertFalse((self.root / self.output).exists())


if __name__ == "__main__":
    unittest.main()
