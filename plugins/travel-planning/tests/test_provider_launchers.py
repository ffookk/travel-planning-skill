from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


amap_launcher = load_module(
    "amap_mcp",
    ROOT / "scripts/providers/amap_mcp.py",
)
flyai_cli = load_module("flyai_cli", ROOT / "scripts/providers/flyai_cli.py")
variflight_launcher = load_module(
    "variflight_mcp",
    ROOT / "scripts/providers/variflight_mcp.py",
)


class ProviderLaunchersTest(unittest.TestCase):
    def test_all_launchers_drop_unrelated_secrets_and_keep_required_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "sources.local.env"
            config.write_text("", encoding="utf-8")
            supplied = {
                "TRAVEL_SOURCES_CONFIG": str(config), "PATH": "/synthetic/bin", "HOME": directory,
                "AMAP_API_KEY": "amap-value", "FLYAI_API_KEY": "flyai-value",
                "VARIFLIGHT_API_KEY": "variflight-value", "PRIVATE_ACCOUNT_TOKEN": "unrelated-value",
            }
            for launcher, expected in (
                (amap_launcher, {"AMAP_API_KEY", "AMAP_MAPS_API_KEY"}),
                (flyai_cli, {"FLYAI_API_KEY"}),
                (variflight_launcher, {"VARIFLIGHT_API_KEY"}),
            ):
                with self.subTest(launcher=launcher.__name__):
                    result = launcher.load_config(supplied)
                    self.assertEqual(set(result), {"PATH", "HOME"} | expected)
                    self.assertEqual(result["PATH"], supplied["PATH"])
                    self.assertEqual(result["HOME"], directory)

    def test_amap_aliases_existing_web_service_key_for_mcp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "sources.local.env"
            config.write_text("AMAP_API_KEY=test-amap-key\n", encoding="utf-8")
            environment = amap_launcher.load_config({"TRAVEL_SOURCES_CONFIG": str(config)})
        self.assertEqual(environment["AMAP_MAPS_API_KEY"], "test-amap-key")
        self.assertNotIn("VARIFLIGHT_API_KEY", environment)

    def test_amap_command_is_version_pinned(self) -> None:
        with patch.object(amap_launcher.shutil, "which", return_value="/usr/local/bin/npx"):
            command = amap_launcher.command()
        self.assertIn("@amap/amap-maps-mcp-server@0.0.8", command)
        self.assertEqual(command[-1], "mcp-amap")

    def test_flyai_command_is_version_pinned(self) -> None:
        with patch.object(flyai_cli.shutil, "which", return_value="/usr/local/bin/npx"):
            command = flyai_cli.command(["search-poi", "--city-name", "杭州"])
        self.assertIn("@fly-ai/flyai-cli@1.0.16", command)
        self.assertEqual(command[-3:], ["search-poi", "--city-name", "杭州"])

    def test_flyai_receives_no_other_provider_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "sources.local.env"
            config.write_text(
                "FLYAI_API_KEY=flyai-key\nVARIFLIGHT_API_KEY=variflight-key\n",
                encoding="utf-8",
            )
            environment = flyai_cli.load_config(
                {"TRAVEL_SOURCES_CONFIG": str(config)}
            )
        self.assertEqual(environment["FLYAI_API_KEY"], "flyai-key")
        self.assertNotIn("VARIFLIGHT_API_KEY", environment)

    def test_variflight_loads_only_its_key_from_user_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "sources.local.env"
            config.write_text(
                "VARIFLIGHT_API_KEY=test-variflight-key\nAMAP_API_KEY=not-loaded\n",
                encoding="utf-8",
            )
            environment = variflight_launcher.load_config(
                {"TRAVEL_SOURCES_CONFIG": str(config)}
            )
        self.assertEqual(environment["VARIFLIGHT_API_KEY"], "test-variflight-key")
        self.assertNotIn("AMAP_API_KEY", environment)

    def test_variflight_commands_are_version_pinned(self) -> None:
        with patch.object(
            variflight_launcher.shutil, "which", return_value="/usr/local/bin/npx"
        ):
            aviation = variflight_launcher.command("aviation")
            tripmatch = variflight_launcher.command("tripmatch")
        self.assertIn("@variflight-ai/variflight-mcp@1.0.3", aviation)
        self.assertIn("@variflight-ai/tripmatch-mcp@0.0.5", tripmatch)
        self.assertEqual(aviation[-1], "variflight-mcp")
        self.assertEqual(tripmatch[-1], "variflight-mcp")


if __name__ == "__main__":
    unittest.main()
