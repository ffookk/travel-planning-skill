#!/usr/bin/env python3
"""Run the pinned autoclaw Xiaohongshu CLI without duplicating its implementation."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_PROJECT = Path(__file__).resolve().parent / "upstream"
CLI = UPSTREAM_PROJECT / "scripts" / "cli.py"
DEFAULT_DATA_ROOT = Path(
    os.environ.get(
        "XDG_DATA_HOME",
        str(Path.home() / ".local" / "share"),
    )
)
CURRENT_RUNTIME_ROOT = DEFAULT_DATA_ROOT / "travel-planning" / "xiaohongshu-skills"
LEGACY_RUNTIME_ROOT = DEFAULT_DATA_ROOT / "travel-itinerary-page" / "xiaohongshu-skills"
DEFAULT_RUNTIME_ROOT = (
    LEGACY_RUNTIME_ROOT
    if LEGACY_RUNTIME_ROOT.exists() and not CURRENT_RUNTIME_ROOT.exists()
    else CURRENT_RUNTIME_ROOT
)
RUNTIME_ROOT = Path(
    os.environ.get(
        "TRAVEL_XHS_HOME",
        str(DEFAULT_RUNTIME_ROOT),
    )
).expanduser().resolve()
VENV_DIR = RUNTIME_ROOT / ".venv"


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        print('{"status":"error","message":"未找到 uv；先运行 skills/xiaohongshu/scripts/setup.py install"}', file=sys.stderr)
        return 2
    if not CLI.is_file():
        print('{"status":"error","message":"插件内置的小红书通用能力不完整，请重新安装插件"}', file=sys.stderr)
        return 2
    if not (VENV_DIR / "pyvenv.cfg").is_file():
        print('{"status":"error","message":"小红书依赖未初始化；先运行 skills/xiaohongshu/scripts/setup.py install"}', file=sys.stderr)
        return 2
    command = [
        uv,
        "run",
        "--frozen",
        "--offline",
        "--project",
        str(UPSTREAM_PROJECT),
        "python",
        str(CLI),
        *sys.argv[1:],
    ]
    environment = dict(os.environ)
    environment["UV_PROJECT_ENVIRONMENT"] = str(VENV_DIR)
    os.execve(uv, command, environment)
    return 2


if __name__ == "__main__":
    sys.exit(main())
