#!/usr/bin/env python3
"""Launch the pinned official AMap MCP server with user-scoped configuration."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from scripts.runtime_env import SourceEnvironmentError, load_source_environment  # noqa: E402


PACKAGE = "@amap/amap-maps-mcp-server"
VERSION = "0.0.8"
EXECUTABLE = "mcp-amap"
ALLOWED_CONFIG_KEYS = {"AMAP_API_KEY", "AMAP_MAPS_API_KEY"}


class AmapMcpError(RuntimeError):
    pass


def load_config(environment: dict[str, str]) -> dict[str, str]:
    return load_source_environment(
        environment,
        allowed_keys=ALLOWED_CONFIG_KEYS,
        aliases={"AMAP_MAPS_API_KEY": ("AMAP_API_KEY",)},
    )


def command() -> list[str]:
    npx = shutil.which("npx")
    if not npx:
        raise AmapMcpError("未找到 npx；高德 MCP 需要 Node.js 22.14.0 或更高版本")
    return [
        npx,
        "--yes",
        "--registry=https://registry.npmjs.org",
        "--package",
        f"{PACKAGE}@{VERSION}",
        EXECUTABLE,
    ]


def main() -> int:
    try:
        environment = load_config(os.environ.copy())
        if not environment.get("AMAP_MAPS_API_KEY"):
            raise AmapMcpError(
                "未配置高德 Web 服务 Key；请设置 AMAP_MAPS_API_KEY 或 AMAP_API_KEY"
            )
        executable = command()
        os.execve(executable[0], executable, environment)
    except (AmapMcpError, SourceEnvironmentError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
