#!/usr/bin/env python3
"""Install dependencies for the vendored autoclaw Xiaohongshu capability."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_PROJECT = SKILL_ROOT / "scripts" / "upstream"
UPSTREAM_SKILL = SKILL_ROOT / "references" / "upstream" / "root.md"
EXTENSION_DIR = SKILL_ROOT / "assets" / "extension"
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
UPSTREAM_URL = "https://github.com/autoclaw-cc/xiaohongshu-skills.git"
UPSTREAM_COMMIT = "b043748282a57e347c52f517dfb59819121134ab"


class SetupError(RuntimeError):
    pass


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run(
    command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None
) -> None:
    try:
        subprocess.run(command, cwd=cwd, env=env, check=True)
    except FileNotFoundError as error:
        raise SetupError(f"缺少命令：{command[0]}") from error
    except subprocess.CalledProcessError as error:
        raise SetupError(f"命令失败（{error.returncode}）：{' '.join(command)}") from error


def vendored_source_present() -> bool:
    required = (
        UPSTREAM_PROJECT / "pyproject.toml",
        UPSTREAM_PROJECT / "uv.lock",
        UPSTREAM_PROJECT / "scripts" / "cli.py",
        UPSTREAM_SKILL,
        EXTENSION_DIR / "manifest.json",
    )
    return all(path.is_file() for path in required)


def install(_: argparse.Namespace) -> dict[str, Any]:
    if shutil.which("uv") is None:
        raise SetupError("未找到 uv；请先安装 uv，再执行安装")
    if not vendored_source_present():
        raise SetupError("插件内置的小红书通用能力不完整，请重新安装插件")
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    environment = dict(os.environ)
    environment["UV_PROJECT_ENVIRONMENT"] = str(VENV_DIR)
    run(["uv", "sync", "--frozen", "--no-dev"], cwd=UPSTREAM_PROJECT, env=environment)
    return installation_payload("installed")


def installation_payload(state: str) -> dict[str, Any]:
    return {
        "status": state,
        "provider": "autoclaw-cc/xiaohongshu-skills",
        "upstream": UPSTREAM_URL,
        "commit": UPSTREAM_COMMIT,
        "integration": "vendored",
        "source_path": str(UPSTREAM_PROJECT),
        "skill_path": str(UPSTREAM_SKILL),
        "extension_path": str(EXTENSION_DIR),
        "runtime_path": str(RUNTIME_ROOT),
        "cli": "python3 skills/xiaohongshu/scripts/cli.py",
        "live_query_available": None,
        "live_query_check": "python3 skills/xiaohongshu/scripts/cli.py check-login",
        "next": "在 chrome://extensions/ 加载 extension_path，然后运行 python3 skills/xiaohongshu/scripts/cli.py check-login",
    }


def status(_: argparse.Namespace) -> dict[str, Any]:
    source_present = vendored_source_present()
    installed = source_present and (VENV_DIR / "pyvenv.cfg").is_file()
    payload = installation_payload("installed" if installed else "not_installed")
    payload.update(
        {
            "source_present": source_present,
            "actual_commit": UPSTREAM_COMMIT if source_present else None,
            "dependencies_installed": (VENV_DIR / "pyvenv.cfg").is_file(),
            "uv_available": shutil.which("uv") is not None,
        }
    )
    return payload


def upstream_skill(_: argparse.Namespace) -> dict[str, Any]:
    if not vendored_source_present():
        raise SetupError("插件内置的小红书通用能力不完整，请重新安装插件")
    return installation_payload("available")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("install", help="安装内置 Skill 的锁定 Python 依赖").set_defaults(handler=install)
    commands.add_parser("status", help="检查安装与依赖状态").set_defaults(handler=status)
    commands.add_parser("upstream-skill", help="返回上游 Skill、扩展和 CLI 路径").set_defaults(handler=upstream_skill)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        emit(args.handler(args))
        return 0
    except (SetupError, OSError, subprocess.CalledProcessError) as error:
        emit({"status": "error", "message": str(error)})
        return 2


if __name__ == "__main__":
    sys.exit(main())
