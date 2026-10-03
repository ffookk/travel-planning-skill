#!/usr/bin/env python3
"""Export an explicit, minimal public summary without copying private itinerary fields."""
from __future__ import annotations

import argparse
import html
import json
import os
import tempfile
from pathlib import Path
from typing import Any


class ShareExportError(ValueError):
    """Invalid selection; messages deliberately omit source values and paths."""


def public_text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ShareExportError("Public labels must be nonblank text of at most 200 characters")
    if any(ord(character) < 32 or 127 <= ord(character) < 160 for character in value):
        raise ShareExportError("Public labels cannot contain control characters")
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ShareExportError("Public labels must contain valid Unicode text")
    return value


def project(data: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    """Only author-selected public labels cross the export boundary."""
    if not isinstance(data, dict) or not isinstance(selection, dict):
        raise ShareExportError("Itinerary and selection must be JSON objects")
    if set(selection) - {"schema_version", "public_title", "attractions"}:
        raise ShareExportError("Selection contains unsupported fields")
    if selection.get("schema_version") != "travel-share-selection/v1":
        raise ShareExportError("Selection must use travel-share-selection/v1")
    title = public_text(selection.get("public_title", "Travel highlights"))
    selected = selection.get("attractions", [])
    if not isinstance(selected, list) or len(selected) > 100:
        raise ShareExportError("Select at most 100 public attraction labels")
    planning = data.get("planning") or {}
    if not isinstance(planning, dict):
        raise ShareExportError("Invalid itinerary planning structure")
    attractions = planning.get("attractions") or []
    days = data.get("days") or []
    if not isinstance(attractions, list) or not isinstance(days, list):
        raise ShareExportError("Invalid itinerary collections")
    ids = set()
    for item in attractions:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise ShareExportError("Attractions must have unique string IDs")
        if item["id"] in ids:
            raise ShareExportError("Attractions must have unique string IDs")
        ids.add(item["id"])
    used = set()
    for day in days:
        if not isinstance(day, dict) or not isinstance(day.get("events", []), list):
            raise ShareExportError("Invalid itinerary events")
        for event in day.get("events", []):
            if not isinstance(event, dict):
                raise ShareExportError("Invalid itinerary events")
            if event.get("type") == "attraction" and isinstance(event.get("attraction_id"), str):
                used.add(event["attraction_id"])
    labels = []
    seen = set()
    for entry in selected:
        if not isinstance(entry, dict) or set(entry) != {"id", "public_label"}:
            raise ShareExportError("Each selection must contain only id and public_label")
        identifier = entry["id"]
        if not isinstance(identifier, str) or identifier not in ids or identifier not in used or identifier in seen:
            raise ShareExportError("Select each used attraction once; lodging and unselected candidates cannot be exported")
        seen.add(identifier)
        labels.append(public_text(entry["public_label"]))
    # Selection order is intentional; original dates, event order, identifiers and names are not copied.
    return {"title": title, "labels": labels}


def build(data: dict[str, Any], selection: dict[str, Any]) -> str:
    public = project(data, selection)
    title = html.escape(public["title"], quote=True)
    items = "".join(f"<li>{html.escape(label, quote=True)}</li>" for label in public["labels"])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="no-referrer"><meta http-equiv="X-DNS-Prefetch-Control" content="off">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>body{{margin:0;background:#faf9f5;color:#24231f;font-family:system-ui,sans-serif;line-height:1.6}}main{{max-width:700px;margin:40px auto;padding:24px}}h1{{line-height:1.2;overflow-wrap:anywhere}}li{{margin:12px 0;overflow-wrap:anywhere}}footer{{margin-top:32px;color:#65665d;font-size:14px}}@media print{{main{{margin:0}}}}</style></head>
<body><main><h1>{title}</h1><ul>{items}</ul><footer>Selected public highlights. This summary omits the private schedule and is not a complete itinerary.</footer></main></body></html>'''


def read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ShareExportError("Cannot read a valid JSON input") from None
    if not isinstance(value, dict):
        raise ShareExportError("JSON inputs must be objects")
    return value


def export(input_path: Path, selection_path: Path, output_path: Path) -> None:
    targets = [path.resolve() for path in (input_path, selection_path, output_path)]
    if len(set(targets)) != 3:
        raise ShareExportError("Input, selection and output must be separate files")
    document = build(read_object(input_path), read_object(selection_path))
    temporary = None
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output_path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(document)
        os.replace(temporary, output_path)
    except OSError:
        raise ShareExportError("Cannot write the share summary") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    args = parser.parse_args()
    try:
        export(args.input, args.selection, args.output)
    except ShareExportError as error:
        parser.exit(1, f"Share export failed: {error}\n")
    print("Share summary written. Review the explicitly selected public labels before sharing.")


if __name__ == "__main__":
    main()
