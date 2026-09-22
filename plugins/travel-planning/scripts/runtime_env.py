"""Load provider credentials through one plugin-level environment contract."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Mapping


SOURCE_KEYS = frozenset(
    {
        "AMAP_API_KEY",
        "AMAP_MAPS_API_KEY",
        "FLYAI_API_KEY",
        "FLYAI_PROFILE",
        "FLYAI_SIGN_SECRET",
        "VARIFLIGHT_API_KEY",
    }
)
PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class SourceEnvironmentError(ValueError):
    """The shared provider environment file is invalid or unreadable."""


def source_config_file(
    environment: Mapping[str, str] | None = None,
    *,
    plugin_root: Path = PLUGIN_ROOT,
) -> Path:
    values = os.environ if environment is None else environment
    custom = values.get("TRAVEL_SOURCES_CONFIG")
    if custom:
        return Path(custom).expanduser().resolve()
    plugin_local = plugin_root / "config" / "sources.local.env"
    if plugin_local.is_file():
        return plugin_local.resolve()
    config_home = Path(values.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    current = config_home / "travel-planning" / "sources.local.env"
    legacy = config_home / "travel-itinerary-page" / "sources.local.env"
    if legacy.is_file() and not current.is_file():
        return legacy.resolve()
    return current.resolve()


def read_source_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise SourceEnvironmentError(f"无法读取数据源配置：{path}") from error

    result: dict[str, str] = {}
    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SourceEnvironmentError(
                f"数据源配置第 {line_number} 行缺少 =：{path}"
            )
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in SOURCE_KEYS:
            raise SourceEnvironmentError(f"数据源配置不支持字段 {key}：{path}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if value:
            result[key] = value
    return result


def load_source_environment(
    environment: Mapping[str, str] | None = None,
    *,
    allowed_keys: Iterable[str] = SOURCE_KEYS,
    config_path: Path | None = None,
    aliases: Mapping[str, tuple[str, ...]] | None = None,
) -> dict[str, str]:
    """Return an inherited environment containing only the requested provider secrets."""
    merged = dict(os.environ if environment is None else environment)
    allowed = frozenset(allowed_keys)
    unknown = allowed - SOURCE_KEYS
    if unknown:
        raise SourceEnvironmentError(
            f"未知数据源环境字段：{', '.join(sorted(unknown))}"
        )

    # Provider subprocesses inherit normal process variables, but not credentials owned by
    # another provider.
    for key in SOURCE_KEYS - allowed:
        merged.pop(key, None)

    configured = read_source_config(config_path or source_config_file(merged))
    for key in allowed:
        if key not in merged and key in configured:
            merged[key] = configured[key]

    for target, candidates in (aliases or {}).items():
        if target not in allowed or merged.get(target):
            continue
        for candidate in candidates:
            if candidate in allowed and merged.get(candidate):
                merged[target] = merged[candidate]
                break
    return merged
