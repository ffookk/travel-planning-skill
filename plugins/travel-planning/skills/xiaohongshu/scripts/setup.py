#!/usr/bin/env python3
"""Install and manage the pinned xpzouying/xiaohongshu-mcp release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from scripts.runtime_env import SourceEnvironmentError, process_environment  # noqa: E402
from scripts.runtime_diagnostics import failure_message, http_failure  # noqa: E402


UPSTREAM_REPOSITORY = "https://github.com/xpzouying/xiaohongshu-mcp"
UPSTREAM_VERSION = "v2.5.0"
UPSTREAM_COMMIT = "6583124dfda92312b6bc19a042a6acfae63fe498"
RELEASE_BASE_URL = f"{UPSTREAM_REPOSITORY}/releases/download/{UPSTREAM_VERSION}"
DEFAULT_ENDPOINT = "http://127.0.0.1:18060"
DEFAULT_DATA_ROOT = Path.home() / ".local" / "share" / "travel-planning" / "xiaohongshu-mcp"
DATA_ROOT = Path(os.environ.get("TRAVEL_XHS_MCP_HOME", DEFAULT_DATA_ROOT)).expanduser().resolve()
RELEASE_DIR = DATA_ROOT / "releases" / UPSTREAM_VERSION
STATE_DIR = DATA_ROOT / "state"
COOKIE_FILE = STATE_DIR / "cookies.json"
PID_FILE = STATE_DIR / "service.pid"
LOG_FILE = STATE_DIR / "service.log"

ASSETS = {
    ("Darwin", "arm64"): {
        "server": (
            "xiaohongshu-mcp-darwin-arm64",
            "3e32e08c3403d22a5efef2f06aa52630b458819fc54474cba23e896c7092c38e",
        ),
        "login": (
            "xiaohongshu-login-darwin-arm64",
            "db5d07c03933b8192dab726d896a028721b096ea452f6e9967ef63a30618ba99",
        ),
    },
    ("Linux", "x86_64"): {
        "server": (
            "xiaohongshu-mcp-linux-amd64",
            "2695820af3a924412c0e555042b81a2598d144342539d4ebea18b17d56c85fbf",
        ),
        "login": (
            "xiaohongshu-login-linux-amd64",
            "367c865f3adc4dfa3407417401a911da313765da12680d1d8f46cae3ea124393",
        ),
    },
}


class SetupError(RuntimeError):
    """The pinned runtime could not be installed or managed safely."""


def output(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _asset_spec() -> dict[str, tuple[str, str]]:
    machine = platform.machine()
    if machine == "AMD64":
        machine = "x86_64"
    spec = ASSETS.get((platform.system(), machine))
    if spec is None:
        raise SetupError(
            f"{UPSTREAM_VERSION} 没有当前平台 {platform.system()}/{machine} 的预编译发布包"
        )
    return spec


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(name: str, digest: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".download")
    request = Request(
        f"{RELEASE_BASE_URL}/{name}",
        headers={"User-Agent": "travel-planning-xiaohongshu-installer/1.0"},
    )
    try:
        with urlopen(request, timeout=300) as response, temporary.open("wb") as stream:
            while chunk := response.read(1024 * 1024):
                stream.write(chunk)
    except HTTPError as error:
        temporary.unlink(missing_ok=True)
        raise SetupError(http_failure(error.code)[1]) from None
    except (URLError, OSError):
        temporary.unlink(missing_ok=True)
        raise SetupError("Runtime download failed; check connectivity and local write permissions") from None
    actual = _sha256(temporary)
    if actual != digest:
        temporary.unlink(missing_ok=True)
        raise SetupError(f"{name} SHA256 不匹配：期望 {digest}，实际 {actual}")
    temporary.chmod(0o755)
    temporary.replace(destination)


def _binary(kind: str) -> Path:
    name, _ = _asset_spec()[kind]
    return RELEASE_DIR / name


def _verify_binary(kind: str) -> bool:
    name, digest = _asset_spec()[kind]
    path = RELEASE_DIR / name
    return path.is_file() and _sha256(path) == digest


def _health(endpoint: str = DEFAULT_ENDPOINT, timeout: float = 2.0) -> bool:
    try:
        with urlopen(f"{endpoint.rstrip('/')}/health", timeout=timeout) as response:
            return response.status == 200
    except (HTTPError, URLError, OSError):
        return False


def _read_pid() -> int | None:
    try:
        return int(PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _process_alive(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _secure_state_files() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        STATE_DIR.chmod(0o700)
    except OSError:
        pass
    for path in (COOKIE_FILE, PID_FILE, LOG_FILE):
        if path.is_file():
            try:
                path.chmod(0o600)
            except OSError:
                pass


def install(_: argparse.Namespace) -> dict[str, Any]:
    installed: list[str] = []
    for kind, (name, digest) in _asset_spec().items():
        destination = RELEASE_DIR / name
        if not (destination.is_file() and _sha256(destination) == digest):
            _download(name, digest, destination)
            installed.append(kind)
    _secure_state_files()
    return {
        "status": "installed",
        "provider": "xpzouying/xiaohongshu-mcp",
        "version": UPSTREAM_VERSION,
        "commit": UPSTREAM_COMMIT,
        "verified_assets": sorted(_asset_spec()),
        "downloaded": sorted(installed),
        "endpoint": f"{DEFAULT_ENDPOINT}/mcp",
        "next": "运行 setup.py start；若预检提示未登录，再运行 setup.py login 并由用户扫码",
    }


def status(_: argparse.Namespace) -> dict[str, Any]:
    _secure_state_files()
    pid = _read_pid()
    server_verified = _verify_binary("server")
    login_verified = _verify_binary("login")
    healthy = _health()
    return {
        "status": "ready" if healthy else ("installed" if server_verified and login_verified else "not_installed"),
        "provider": "xpzouying/xiaohongshu-mcp",
        "version": UPSTREAM_VERSION,
        "commit": UPSTREAM_COMMIT,
        "assets_verified": {"server": server_verified, "login": login_verified},
        "service": {
            "healthy": healthy,
            "managed_pid": pid,
            "managed_process_alive": _process_alive(pid),
            "endpoint": f"{DEFAULT_ENDPOINT}/mcp",
        },
        "cookie_file_present": COOKIE_FILE.is_file(),
        "data_root": str(DATA_ROOT),
    }


def start(args: argparse.Namespace) -> dict[str, Any]:
    if not _verify_binary("server"):
        raise SetupError("尚未安装或发布包校验失败；先运行 setup.py install")
    if _health():
        return status(args)
    _secure_state_files()
    environment = process_environment()
    environment["COOKIES_PATH"] = str(COOKIE_FILE)
    try:
        with LOG_FILE.open("ab") as log:
            process = subprocess.Popen(
                [str(_binary("server")), "-headless=true", "-port=127.0.0.1:18060"],
                cwd=STATE_DIR,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except OSError:
        raise SetupError(failure_message("runtime_unavailable")) from None
    _secure_state_files()
    PID_FILE.write_text(f"{process.pid}\n", encoding="utf-8")
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        if _health():
            _secure_state_files()
            return status(args)
        if process.poll() is not None:
            raise SetupError(f"xiaohongshu-mcp failed to start (exit {process.returncode}); raw local logs were withheld")
        time.sleep(0.5)
    raise SetupError(f"xiaohongshu-mcp 在 {args.timeout} 秒内未就绪；查看 {LOG_FILE}")


def stop(_: argparse.Namespace) -> dict[str, Any]:
    pid = _read_pid()
    if not _process_alive(pid):
        PID_FILE.unlink(missing_ok=True)
        return {"status": "stopped", "managed_process_found": False}
    assert pid is not None
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and _process_alive(pid):
        time.sleep(0.2)
    if _process_alive(pid):
        raise SetupError(f"进程 {pid} 未在 10 秒内停止")
    PID_FILE.unlink(missing_ok=True)
    return {"status": "stopped", "managed_process_found": True, "pid": pid}


def login(_: argparse.Namespace) -> dict[str, Any]:
    if not _verify_binary("login"):
        raise SetupError("尚未安装或发布包校验失败；先运行 setup.py install")
    if _health():
        raise SetupError("请先运行 setup.py stop，避免登录工具与 MCP 服务同时使用同一 Cookie 文件")
    _secure_state_files()
    environment = process_environment()
    environment["COOKIES_PATH"] = str(COOKIE_FILE)
    try:
        with LOG_FILE.open("ab") as log:
            completed = subprocess.run(
                [str(_binary("login"))], cwd=STATE_DIR, env=environment,
                stdout=log, stderr=subprocess.STDOUT, check=False,
            )
    except OSError:
        raise SetupError(failure_message("runtime_unavailable")) from None
    finally:
        _secure_state_files()
    if completed.returncode != 0:
        raise SetupError(f"登录工具退出码为 {completed.returncode}")
    _secure_state_files()
    return {"status": "login_completed", "cookie_file_present": COOKIE_FILE.is_file()}


def logs(args: argparse.Namespace) -> dict[str, Any]:
    if not LOG_FILE.is_file():
        return {"status": "empty", "log_file": str(LOG_FILE), "lines": []}
    return {
        "status": "withheld", "log_file": str(LOG_FILE), "lines": [],
        "message": "Raw runtime logs may contain account data or tokens; inspect the local file privately if needed",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("install", help="下载并校验固定版本的服务与登录工具").set_defaults(handler=install)
    subparsers.add_parser("status", help="检查安装、进程和 HTTP 健康状态").set_defaults(handler=status)
    start_parser = subparsers.add_parser("start", help="在后台启动本地 MCP 服务")
    start_parser.add_argument("--timeout", type=int, default=300, choices=range(5, 601), metavar="5-600")
    start_parser.set_defaults(handler=start)
    subparsers.add_parser("stop", help="停止由本脚本启动的 MCP 服务").set_defaults(handler=stop)
    subparsers.add_parser("login", help="打开上游独立浏览器登录工具，由用户扫码").set_defaults(handler=login)
    logs_parser = subparsers.add_parser("logs", help="Report local log availability without exposing raw content")
    logs_parser.add_argument("--lines", type=int, default=40, choices=range(1, 501), metavar="1-500", help="Accepted for compatibility; raw lines remain private")
    logs_parser.set_defaults(handler=logs)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        output(args.handler(args))
        return 0
    except (SetupError, SourceEnvironmentError) as error:
        output({"status": "error", "message": str(error)})
        return 2


if __name__ == "__main__":
    sys.exit(main())
