#!/usr/bin/env python3
"""Build a marketplace ZIP with Git inclusion and private runtime path guards."""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLUGIN_DIR = Path("plugins/travel-planning")
DEFAULT_MARKETPLACE_FILE = Path(".agents/plugins/marketplace.json")
DEFAULT_OUTPUT = Path("output/travel-planning-marketplace.zip")
DEFAULT_BUNDLE_NAME = "travel-planning-marketplace"
PRIVATE_DIRECTORIES = frozenset({
    ".travel-research", ".travel-tools", ".playwright-cli", ".cache",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules",
})
PRIVATE_FILENAMES = frozenset({
    "cookies.json", "cookies.txt", "search-tokens.json", "service.pid",
    "storage-state.json", "storage_state.json",
})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plugin-dir",
        type=Path,
        default=DEFAULT_PLUGIN_DIR,
        help=f"plugin directory relative to the repository (default: {DEFAULT_PLUGIN_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"ZIP path relative to the repository (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--bundle-name",
        default=DEFAULT_BUNDLE_NAME,
        help=f"top-level directory inside the ZIP (default: {DEFAULT_BUNDLE_NAME})",
    )
    return parser.parse_args()


def repository_relative(path: Path, argument_name: str) -> Path:
    resolved = path.resolve() if path.is_absolute() else (REPOSITORY_ROOT / path).resolve()
    try:
        return resolved.relative_to(REPOSITORY_ROOT)
    except ValueError as error:
        raise SystemExit(f"{argument_name} must stay inside the repository") from error


def is_private_runtime_path(path: Path) -> bool:
    """Reject known private paths, independently of Git's tracking/ignore state.

    This is a path policy, not a content-complete secret detector.
    """
    parts = tuple(part.casefold() for part in path.parts)
    if any(part in PRIVATE_DIRECTORIES for part in parts):
        return True
    name = parts[-1] if parts else ""
    if name in PRIVATE_FILENAMES or name.startswith("sources.local.env"):
        return True
    if name != "sources.example.env" and (
        name == ".env" or ".env." in name or name.endswith(".env")
    ):
        return True
    return name.endswith((".log", ".pid", ".pyc", ".pyo")) or ".log." in name


def validate_package_files(files: list[Path]) -> None:
    """Validate every path and symlink before creating any archive output."""
    included = set(files)
    for relative_path in files:
        def refuse(reason: str) -> None:
            raise SystemExit(f"Refusing to package {relative_path.as_posix()}: {reason}")

        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise SystemExit("Package entries must be repository-relative paths")
        if is_private_runtime_path(relative_path):
            refuse("private runtime path")

        # Walk each link component so an intermediate private target cannot be
        # hidden by another symlink. Absolute links also expose host paths and
        # are not portable, even when their current target is inside the repo.
        pending = list(relative_path.parts)
        resolved = REPOSITORY_ROOT
        links = 0
        while pending:
            component = pending.pop(0)
            if component == ".":
                continue
            if component == "..":
                if resolved == REPOSITORY_ROOT:
                    refuse("symlink target leaves the repository")
                resolved = resolved.parent
                continue
            candidate = resolved / component
            if is_private_runtime_path(candidate.relative_to(REPOSITORY_ROOT)):
                refuse("symlink target is a private runtime path")
            if candidate.is_symlink():
                links += 1
                if links > 40:
                    refuse("symlink target is cyclic or too deeply nested")
                target = Path(os.readlink(candidate))
                if target.is_absolute():
                    refuse("absolute symlink target")
                pending = list(target.parts) + pending
            else:
                resolved = candidate

        if links:
            if not resolved.exists():
                refuse("symlink target does not exist")
            target_relative = resolved.relative_to(REPOSITORY_ROOT)
            if target_relative not in included and not (
                resolved.is_dir() and any(target_relative in path.parents for path in included)
            ):
                refuse("symlink target is outside the package file set")


def package_files(plugin_dir: Path) -> list[Path]:
    included_paths = [Path("README.md"), DEFAULT_MARKETPLACE_FILE, plugin_dir]
    result = subprocess.run(
        [
            "git",
            "-C",
            os.fspath(REPOSITORY_ROOT),
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            *(os.fspath(path) for path in included_paths),
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    candidates = [Path(os.fsdecode(item)) for item in result.stdout.split(b"\0") if item]
    return sorted(
        path
        for path in candidates
        if (REPOSITORY_ROOT / path).is_symlink() or (REPOSITORY_ROOT / path).is_file()
    )


def add_symlink(archive: zipfile.ZipFile, source: Path, archive_name: Path) -> None:
    mode = source.lstat().st_mode
    info = zipfile.ZipInfo(archive_name.as_posix())
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | stat.S_IMODE(mode)) << 16
    archive.writestr(info, os.readlink(source).encode())


def build_archive(plugin_dir: Path, output: Path, bundle_name: str) -> int:
    source_root = REPOSITORY_ROOT / plugin_dir
    if not source_root.is_dir():
        raise SystemExit(f"plugin directory does not exist: {plugin_dir}")
    if not (source_root / ".codex-plugin/plugin.json").is_file():
        raise SystemExit(f"missing plugin manifest: {plugin_dir / '.codex-plugin/plugin.json'}")
    if not (REPOSITORY_ROOT / DEFAULT_MARKETPLACE_FILE).is_file():
        raise SystemExit(
            f"missing marketplace catalog: {DEFAULT_MARKETPLACE_FILE}"
        )

    files = package_files(plugin_dir)
    if not files:
        raise SystemExit(f"no packageable files found under {plugin_dir}")
    validate_package_files(files)

    output_path = REPOSITORY_ROOT / output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)

    try:
        with zipfile.ZipFile(
            temporary_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for relative_path in files:
                source = REPOSITORY_ROOT / relative_path
                archive_name = Path(bundle_name) / relative_path
                if source.is_symlink():
                    add_symlink(archive, source, archive_name)
                else:
                    archive.write(source, archive_name.as_posix())
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return len(files)


def main() -> None:
    args = parse_args()
    plugin_dir = repository_relative(args.plugin_dir, "--plugin-dir")
    output = repository_relative(args.output, "--output")
    bundle_name = args.bundle_name.strip()
    if not bundle_name or Path(bundle_name).name != bundle_name or bundle_name in {".", ".."}:
        raise SystemExit("--bundle-name must be one directory name")
    if output == plugin_dir or plugin_dir in output.parents:
        raise SystemExit("--output must not be inside the plugin directory")

    file_count = build_archive(plugin_dir, output, bundle_name)
    print(f"Created {REPOSITORY_ROOT / output} ({file_count} files)")


if __name__ == "__main__":
    main()
