from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.runtime_env import source_config_file


class RuntimeEnvironmentTest(unittest.TestCase):
    def test_explicit_config_has_highest_file_priority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            explicit = root / "explicit.env"
            self.assertEqual(
                source_config_file(
                    {"TRAVEL_SOURCES_CONFIG": str(explicit)}, plugin_root=root
                ),
                explicit.resolve(),
            )

    def test_plugin_local_config_precedes_user_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "plugin"
            local = root / "config" / "sources.local.env"
            local.parent.mkdir(parents=True)
            local.write_text("AMAP_API_KEY=test\n", encoding="utf-8")
            config_home = Path(directory) / "user-config"
            self.assertEqual(
                source_config_file(
                    {"XDG_CONFIG_HOME": str(config_home)}, plugin_root=root
                ),
                local.resolve(),
            )

    def test_user_config_is_fallback_when_plugin_local_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "plugin"
            config_home = Path(directory) / "user-config"
            self.assertEqual(
                source_config_file(
                    {"XDG_CONFIG_HOME": str(config_home)}, plugin_root=root
                ),
                (config_home / "travel-planning" / "sources.local.env").resolve(),
            )

    def test_legacy_user_config_is_reused_when_new_path_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "plugin"
            config_home = Path(directory) / "user-config"
            legacy = config_home / "travel-itinerary-page" / "sources.local.env"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("AMAP_API_KEY=test\n", encoding="utf-8")
            self.assertEqual(
                source_config_file(
                    {"XDG_CONFIG_HOME": str(config_home)}, plugin_root=root
                ),
                legacy.resolve(),
            )


if __name__ == "__main__":
    unittest.main()
