"""Write local travel artifacts atomically with owner-only POSIX permissions."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def check_target(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise OSError("Artifact output must be a regular file, not a symlink or directory")


def write_private_text(path: Path, text: str) -> None:
    """Replace one complete UTF-8 artifact without changing its parent permissions."""
    check_target(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = None
    temporary = None
    try:
        descriptor, name = tempfile.mkstemp(prefix=".travel-artifact-", dir=path.parent)
        temporary = Path(name)
        if os.name == "posix":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            descriptor = None
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        check_target(path)
        os.replace(temporary, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if temporary is not None:
            temporary.unlink(missing_ok=True)
