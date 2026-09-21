from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parents[1]


class PluginLayoutTest(unittest.TestCase):
    def test_only_five_user_visible_skills_are_registered(self) -> None:
        skill_files = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "skills").rglob("SKILL.md"))
        self.assertEqual(
            skill_files,
            [
                "skills/amap-maps/SKILL.md",
                "skills/flyai/SKILL.md",
                "skills/travel-planning/SKILL.md",
                "skills/variflight/SKILL.md",
                "skills/xiaohongshu/SKILL.md",
            ],
        )

    def test_mcp_skills_guide_existing_servers_without_provider_scripts(self) -> None:
        self.assertTrue((ROOT / "skills/amap-maps/references/tool-routing.md").is_file())
        self.assertTrue((ROOT / "skills/variflight/references/tool-routing.md").is_file())
        self.assertFalse((ROOT / "skills/amap-maps/scripts").exists())
        self.assertFalse((ROOT / "skills/variflight/scripts").exists())

    def test_flyai_is_one_vendored_skill(self) -> None:
        self.assertTrue((ROOT / "scripts/providers/flyai_cli.py").is_file())
        self.assertTrue((ROOT / "skills/flyai/references/upstream.lock.json").is_file())

    def test_expected_mcp_servers_are_registered(self) -> None:
        manifest = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
        servers = manifest["mcpServers"]
        self.assertEqual(
            set(servers),
            {"amap-maps", "variflight-aviation", "variflight-tripmatch"},
        )
        self.assertEqual(
            servers["amap-maps"]["args"],
            ["./scripts/providers/amap_mcp.py"],
        )
        self.assertEqual(
            servers["variflight-aviation"]["args"],
            [
                "./scripts/providers/variflight_mcp.py",
                "aviation",
            ],
        )
        self.assertEqual(
            servers["variflight-tripmatch"]["args"],
            [
                "./scripts/providers/variflight_mcp.py",
                "tripmatch",
            ],
        )

    def test_xiaohongshu_capability_is_vendored_inside_its_skill(self) -> None:
        required = (
            ROOT / "skills/xiaohongshu/scripts/upstream/uv.lock",
            ROOT / "skills/xiaohongshu/scripts/upstream/scripts/cli.py",
            ROOT / "skills/xiaohongshu/assets/extension/manifest.json",
            ROOT / "skills/xiaohongshu/references/upstream/root.md",
        )
        self.assertTrue(all(path.is_file() for path in required))

    def test_runtime_secrets_are_ignored_by_source_control(self) -> None:
        self.assertTrue((ROOT / "config/sources.example.env").is_file())
        self.assertFalse((ROOT / "config/sources.local.env").exists())
        repository_ignore = REPOSITORY_ROOT / ".gitignore"
        if repository_ignore.is_file():
            ignored = repository_ignore.read_text(encoding="utf-8").splitlines()
            self.assertIn("/config/sources.local.env", ignored)
            self.assertTrue((REPOSITORY_ROOT / "config/sources.local.env").is_file())
        self.assertFalse((ROOT / ".travel-tools").exists())

    def test_provider_runtime_is_not_nested_inside_skills(self) -> None:
        self.assertFalse((ROOT / "skills/flyai/scripts").exists())
        self.assertFalse((ROOT / "skills/travel-planning/config").exists())
        self.assertFalse(
            (ROOT / "skills/travel-planning/scripts/amap_mcp_server.py").exists()
        )
        self.assertFalse(
            (ROOT / "skills/travel-planning/scripts/variflight_mcp_server.py").exists()
        )

    def test_legacy_top_level_integration_directories_are_absent(self) -> None:
        self.assertFalse((ROOT / "integrations").exists())
        self.assertFalse((ROOT / "third_party").exists())


if __name__ == "__main__":
    unittest.main()
