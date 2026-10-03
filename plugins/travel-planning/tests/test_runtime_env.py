from __future__ import annotations

import tempfile
import traceback
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.runtime_env import SourceEnvironmentError, load_source_environment, process_environment, read_source_config, source_config_file


class RuntimeEnvironmentTest(unittest.TestCase):
    def test_invalid_configuration_diagnostics_omit_keys_values_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "SYNTHETIC-PRIVATE-PATH.env"
            for contents, expected in (
                ("# comment\nSYNTHETIC_PRIVATE_KEY=private-value\n", "数据源配置不支持字段"),
                ("# comment\nSYNTHETIC_PRIVATE_MALFORMED\n", "数据源配置第 2 行缺少 ="),
            ):
                with self.subTest(expected=expected):
                    config.write_text(contents, encoding="utf-8")
                    with self.assertRaises(SourceEnvironmentError) as raised:
                        read_source_config(config)
                    diagnostic = str(raised.exception)
                    self.assertIn(expected, diagnostic)
                    self.assertIn("2", diagnostic)
                    self.assertNotIn("SYNTHETIC", diagnostic)
                    self.assertNotIn("private-value", diagnostic)
                    self.assertNotIn(str(config), diagnostic)
        with self.assertRaises(SourceEnvironmentError) as raised:
            load_source_environment({}, allowed_keys={"SYNTHETIC_PRIVATE_ALLOWED_KEY"})
        self.assertIn("未知数据源环境字段", str(raised.exception))
        self.assertNotIn("SYNTHETIC", str(raised.exception))

    def test_configuration_read_failures_withhold_private_exception_details(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "SYNTHETIC-PRIVATE-PATH.env"
            config.write_text("", encoding="utf-8")
            errors = (
                OSError(f"SYNTHETIC_PRIVATE_FAILURE: {config}"),
                UnicodeDecodeError("utf-8", b"\xff", 0, 1, "SYNTHETIC_PRIVATE_FAILURE"),
            )
            for error in errors:
                with self.subTest(error=type(error).__name__), patch.object(Path, "read_text", side_effect=error):
                    try:
                        read_source_config(config)
                    except SourceEnvironmentError as failure:
                        diagnostic = traceback.format_exc()
                        self.assertIn("无法读取数据源配置", str(failure))
                        self.assertNotIn("SYNTHETIC", diagnostic)
                        self.assertNotIn(str(config), diagnostic)
                        self.assertTrue(failure.__suppress_context__)
                    else:
                        self.fail("Expected a private configuration read failure")

    def test_process_environment_defaults_to_os_runtime_variables_only(self) -> None:
        supplied = {
            "PATH": "/synthetic/bin", "HOME": "/synthetic/home", "LANG": "en_US.UTF-8",
            "XDG_CACHE_HOME": "/synthetic/cache", "DISPLAY": ":5",
            "CUSTOM_ACCOUNT_SECRET": "private-value", "AWS_SESSION_TOKEN": "cloud-value",
            "GITHUB_TOKEN": "repository-value", "HTTPS_PROXY": "https://private-proxy.test",
            "NODE_OPTIONS": "--require private.js", "FLYAI_API_KEY": "provider-value",
        }
        self.assertEqual(process_environment(supplied), {
            key: supplied[key] for key in ("PATH", "HOME", "LANG", "XDG_CACHE_HOME", "DISPLAY")
        })

    def test_passthrough_requires_explicit_valid_nonreserved_names(self) -> None:
        self.assertEqual(process_environment({
            "TRAVEL_PROVIDER_ENV_PASSTHROUGH": "HTTPS_PROXY, NODE_EXTRA_CA_CERTS",
            "HTTPS_PROXY": "https://synthetic-proxy.test", "NODE_EXTRA_CA_CERTS": "/synthetic/ca.pem",
            "UNRELATED_SECRET": "private-value",
        }), {"HTTPS_PROXY": "https://synthetic-proxy.test", "NODE_EXTRA_CA_CERTS": "/synthetic/ca.pem"})
        for names in ("VARIFLIGHT_API_KEY", "FLYAI_API_KEY", "NODE_OPTIONS", "DYLD_INSERT_LIBRARIES", "LD_PRELOAD", "COOKIES_PATH", "NAME=private-value", "PATH,,HOME"):
            with self.subTest(names=names):
                with self.assertRaises(SourceEnvironmentError) as raised:
                    process_environment({"TRAVEL_PROVIDER_ENV_PASSTHROUGH": names})
                self.assertNotIn(names, str(raised.exception))

    def test_minimization_keeps_config_selection_and_credential_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "synthetic.env"
            config.write_text("FLYAI_API_KEY=config-value\nVARIFLIGHT_API_KEY=other-value\n", encoding="utf-8")
            result = load_source_environment({
                "TRAVEL_SOURCES_CONFIG": str(config), "HOME": directory,
                "FLYAI_API_KEY": "environment-value", "UNKNOWN_SECRET": "private-value",
            }, allowed_keys={"FLYAI_API_KEY"})
        self.assertEqual(result, {"HOME": directory, "FLYAI_API_KEY": "environment-value"})

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
