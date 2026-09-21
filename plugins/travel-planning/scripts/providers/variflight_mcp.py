#!/usr/bin/env python3
"""Launch a pinned Variflight MCP server with user-scoped credentials."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from scripts.runtime_env import SourceEnvironmentError, load_source_environment  # noqa: E402


SERVERS = {
    "aviation": ("@variflight-ai/variflight-mcp", "1.0.3"),
    "tripmatch": ("@variflight-ai/tripmatch-mcp", "0.0.5"),
}
EXECUTABLE = "variflight-mcp"


class VariflightMcpError(RuntimeError):
    pass


def load_config(environment: dict[str, str]) -> dict[str, str]:
    return load_source_environment(
        environment,
        allowed_keys={"VARIFLIGHT_API_KEY"},
    )


def command(server: str) -> list[str]:
    if server not in SERVERS:
        raise VariflightMcpError(f"未知飞常准 MCP：{server}")
    npx = shutil.which("npx")
    if not npx:
        raise VariflightMcpError("未找到 npx；飞常准 MCP 需要 Node.js 18 或更高版本")
    package, version = SERVERS[server]
    return [
        npx,
        "--yes",
        "--registry=https://registry.npmjs.org",
        "--package",
        f"{package}@{version}",
        EXECUTABLE,
    ]


def main() -> int:
    try:
        if len(sys.argv) != 2:
            raise VariflightMcpError("用法：variflight_mcp.py aviation|tripmatch")
        environment = load_config(os.environ.copy())
        if not environment.get("VARIFLIGHT_API_KEY"):
            raise VariflightMcpError(
                "未配置飞常准 Key；请在用户配置中设置 VARIFLIGHT_API_KEY"
            )
        executable = command(sys.argv[1])
        os.execve(executable[0], executable, environment)
    except (VariflightMcpError, SourceEnvironmentError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
