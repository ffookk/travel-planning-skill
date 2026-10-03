#!/usr/bin/env python3
"""List installed scenario references without loading trip data or providers."""

from __future__ import annotations

import argparse
import json
import re
import stat
import sys
from pathlib import Path
from typing import Any


GUIDE_DIRECTORY = Path(__file__).resolve().parents[1] / "references" / "scenarios"
HEADER_PREFIX = "<!-- travel-guide: "
HEADER_SUFFIX = " -->"
MAX_HEADER_BYTES = 8192
FIELDS = {"id", "title", "category", "when", "tags"}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class CatalogError(ValueError):
    """An installed guide has an invalid or unreadable discovery header."""


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CatalogError("Guide metadata contains duplicate keys")
        result[key] = value
    return result


def read_card(path: Path) -> dict[str, Any]:
    """Read only a bounded first line from a regular installed Markdown file."""
    try:
        if not stat.S_ISREG(path.lstat().st_mode):
            raise CatalogError("Guide references must be regular files")
        with path.open("rb") as stream:
            raw = stream.readline(MAX_HEADER_BYTES + 1)
        if len(raw) > MAX_HEADER_BYTES:
            raise CatalogError("Guide metadata exceeds the discovery size limit")
        line = raw.decode("utf-8").rstrip("\r\n")
        if not line.startswith(HEADER_PREFIX) or not line.endswith(HEADER_SUFFIX):
            raise CatalogError("Guide discovery metadata is missing")
        card = json.loads(line[len(HEADER_PREFIX):-len(HEADER_SUFFIX)], object_pairs_hook=unique_object)
    except CatalogError:
        raise
    except (OSError, ValueError, RecursionError):
        raise CatalogError("Guide discovery metadata could not be read") from None
    if not isinstance(card, dict) or set(card) != FIELDS:
        raise CatalogError("Guide discovery metadata has invalid fields")
    for key, limit in (("id", 80), ("title", 160), ("category", 40), ("when", 600)):
        value = card[key]
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise CatalogError("Guide discovery metadata has an invalid text field")
        if any(ord(character) < 32 or 0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise CatalogError("Guide discovery metadata has invalid text encoding")
    if not SLUG.fullmatch(card["id"]) or card["id"] != path.stem or not SLUG.fullmatch(card["category"]):
        raise CatalogError("Guide identifiers must match their installed filenames")
    tags = card["tags"]
    if not isinstance(tags, list) or not tags or len(tags) > 24:
        raise CatalogError("Guide discovery tags must be a nonempty array")
    for tag in tags:
        if not isinstance(tag, str) or not tag.strip() or len(tag) > 100:
            raise CatalogError("Guide discovery tags must be short text")
        if any(ord(character) < 32 or 0xD800 <= ord(character) <= 0xDFFF for character in tag):
            raise CatalogError("Guide discovery tags have invalid text encoding")
    return {**card, "path": f"references/scenarios/{path.name}"}


def list_guides(directory: Path = GUIDE_DIRECTORY, *, query: str = "", category: str | None = None) -> list[dict[str, Any]]:
    """Return deterministic discovery cards; every query word must match a card."""
    try:
        if directory.is_symlink():
            raise CatalogError("The guide directory must not be a symlink")
        if not directory.exists():
            return []
        if not directory.is_dir():
            raise CatalogError("The guide location must be a directory")
        paths = sorted(directory.glob("*.md"))
    except OSError:
        raise CatalogError("The installed guide directory could not be read") from None
    cards = [read_card(path) for path in paths]
    words = query.casefold().split()
    return [card for card in cards
            if (category is None or card["category"] == category)
            and all(word in " ".join([card["title"], card["when"], *card["tags"]]).casefold() for word in words)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", default="", help="case-insensitive words to match in title, trigger, or tags")
    parser.add_argument("--category", help="restrict results to one installed category")
    args = parser.parse_args(argv)
    try:
        guides = list_guides(query=args.query, category=args.category)
    except CatalogError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps({"guides": guides}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
