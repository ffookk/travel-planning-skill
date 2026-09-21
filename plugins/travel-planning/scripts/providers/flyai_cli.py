#!/usr/bin/env python3
"""Run the pinned FlyAI CLI with user-scoped credentials."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from scripts.runtime_env import SourceEnvironmentError, load_source_environment  # noqa: E402


PACKAGE = "@fly-ai/flyai-cli"
VERSION = "1.0.16"
EXECUTABLE = "flyai"
ALLOWED_CONFIG_KEYS = {"FLYAI_API_KEY", "FLYAI_SIGN_SECRET", "FLYAI_PROFILE"}


def load_config(environment: dict[str, str]) -> dict[str, str]:
    return load_source_environment(environment, allowed_keys=ALLOWED_CONFIG_KEYS)


def command(arguments: list[str]) -> list[str]:
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("未找到 npx；飞猪 FlyAI 需要 Node.js 18 或更高版本")
    return [
        npx,
        "--yes",
        "--registry=https://registry.npmjs.org",
        "--package",
        f"{PACKAGE}@{VERSION}",
        EXECUTABLE,
        *arguments,
    ]


def main() -> int:
    try:
        executable = command(sys.argv[1:])
        environment = load_config(os.environ.copy())
    except (RuntimeError, SourceEnvironmentError) as error:
        print(str(error), file=sys.stderr)
        return 2
    os.execve(executable[0], executable, environment)
    return 2


if __name__ == "__main__":
    sys.exit(main())
