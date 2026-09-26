"""Load provider credentials through one plugin-level environment contract."""

from __future__ import annotations

import os
import re
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
RUNTIME_KEYS = frozenset({
    "PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT",
    "TEMP", "TMP", "TMPDIR", "LANG", "LANGUAGE", "LC_ALL", "LC_CTYPE", "LC_MESSAGES", "TZ",
    "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_RUNTIME_DIR",
    "DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS",
})
PASSTHROUGH_SETTING = "TRAVEL_PROVIDER_ENV_PASSTHROUGH"
BLOCKED_PASSTHROUGH_KEYS = SOURCE_KEYS | {
    "TRAVEL_SOURCES_CONFIG", PASSTHROUGH_SETTING, "COOKIES_PATH",
    "NODE_OPTIONS", "NODE_PATH", "PYTHONPATH", "PYTHONHOME", "BASH_ENV", "ENV",
}


class SourceEnvironmentError(ValueError):
    """The shared provider environment file is invalid or unreadable."""


def process_environment(environment: Mapping[str, str] | None = None) -> dict[str, str]:
    """Pass OS runtime settings and explicitly named extras, never the entire environment."""
    values = os.environ if environment is None else environment
    extra = values.get(PASSTHROUGH_SETTING, "")
    if not isinstance(extra, str):
        raise SourceEnvironmentError("Provider environment passthrough must be a comma-separated list of names")
    names = {name.strip() for name in extra.split(",")} if extra.strip() else set()
    for name in names:
        upper = name.upper()
        if (
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
            or upper in BLOCKED_PASSTHROUGH_KEYS
            or upper.startswith(("LD_", "DYLD_"))
        ):
            raise SourceEnvironmentError("Provider environment passthrough contains an invalid or reserved name")
    return {key: value for key, value in values.items() if key in RUNTIME_KEYS or key in names}


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
    except (OSError, UnicodeError):
        raise SourceEnvironmentError("无法读取数据源配置；请检查文件权限和 UTF-8 编码") from None

    result: dict[str, str] = {}
    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SourceEnvironmentError(
                f"数据源配置第 {line_number} 行缺少 ="
            )
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in SOURCE_KEYS:
            raise SourceEnvironmentError(f"数据源配置不支持字段（第 {line_number} 行）；请使用受支持的供应商配置名称")
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
    """Return a minimal runtime environment with only this provider's configured secrets."""
    inherited = os.environ if environment is None else environment
    allowed = frozenset(allowed_keys)
    unknown = allowed - SOURCE_KEYS
    if unknown:
        raise SourceEnvironmentError(
            "未知数据源环境字段；请使用受支持的供应商配置名称"
        )

    merged = process_environment(inherited)
    configured = read_source_config(config_path or source_config_file(inherited))
    for key in allowed:
        if key in inherited:
            merged[key] = inherited[key]
        elif key in configured:
            merged[key] = configured[key]

    for target, candidates in (aliases or {}).items():
        if target not in allowed or merged.get(target):
            continue
        for candidate in candidates:
            if candidate in allowed and merged.get(candidate):
                merged[target] = merged[candidate]
                break
    return merged
