#!/usr/bin/env python3
"""Verify explicitly supplied final-delivery files against a local, unsigned receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


BINDING_FIELDS = ("itinerary_sha256", "html_sha256", "research_sha256", "decisions_sha256", "export_profile")
RECEIPT_FIELDS = {
    "schema_version", "status", *BINDING_FIELDS, "binding_sha256", "checked_at",
    "warning_count", "checked_event_count", "conflicts",
}
PROFILES = {"regular", "private-offline"}
MAX_RECEIPT_BYTES = 65536


class VerificationError(ValueError):
    """Verification failed; messages contain no file paths or supplied values."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def is_digest(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def is_count(value: Any) -> bool:
    return type(value) is int and value >= 0


def load_receipt(path: Path) -> dict[str, Any]:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError
            value[key] = item
        return value

    def reject_constant(_: str) -> None:
        raise ValueError

    try:
        if not path.is_file():
            raise ValueError
        with path.open("rb") as stream:
            raw = stream.read(MAX_RECEIPT_BYTES + 1)
        if len(raw) > MAX_RECEIPT_BYTES:
            raise ValueError
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object, parse_constant=reject_constant)
    except (OSError, ValueError, RecursionError):
        raise VerificationError("Cannot read a valid receipt JSON object within the size limit") from None
    if not isinstance(value, dict) or set(value) != RECEIPT_FIELDS:
        raise VerificationError("Receipt fields do not match the supported schema")
    return value


def validate_receipt(receipt: dict[str, Any]) -> None:
    if receipt["schema_version"] != "itinerary-final-delivery/v1" or receipt["status"] != "pass":
        raise VerificationError("Receipt version or delivery status is unsupported")
    if not isinstance(receipt["export_profile"], str) or receipt["export_profile"] not in PROFILES:
        raise VerificationError("Receipt export profile is unsupported")
    if any(not is_digest(receipt[key]) for key in ("itinerary_sha256", "html_sha256", "binding_sha256")):
        raise VerificationError("Receipt contains an invalid required digest")
    if any(receipt[key] is not None and not is_digest(receipt[key]) for key in ("research_sha256", "decisions_sha256")):
        raise VerificationError("Receipt contains an invalid optional digest")
    if not is_count(receipt["warning_count"]) or not is_count(receipt["checked_event_count"]):
        raise VerificationError("Receipt audit counts are invalid")
    try:
        checked = receipt["checked_at"]
        if not isinstance(checked, str) or datetime.fromisoformat(checked.replace("Z", "+00:00")).utcoffset() is None:
            raise ValueError
    except ValueError:
        raise VerificationError("Receipt audit time requires an ISO date-time with a UTC offset") from None
    conflicts = receipt["conflicts"]
    if receipt["research_sha256"] is None:
        if receipt["decisions_sha256"] is not None or conflicts != {"status": "conflicts_not_checked"}:
            raise VerificationError("Receipt research and conflict declarations are inconsistent")
    elif (not isinstance(conflicts, dict)
          or set(conflicts) != {"status", "resolved_conflict_count", "unused_conflict_count"}
          or conflicts["status"] != "checked"
          or not is_count(conflicts["resolved_conflict_count"])
          or not is_count(conflicts["unused_conflict_count"])):
        raise VerificationError("Receipt research and conflict declarations are inconsistent")
    binding = {key: receipt[key] for key in BINDING_FIELDS}
    if hashlib.sha256(canonical(binding)).hexdigest() != receipt["binding_sha256"]:
        raise VerificationError("Receipt binding digest does not match its recorded fields")


def file_digest(path: Path) -> str:
    try:
        if not path.is_file():
            raise ValueError
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except (OSError, ValueError):
        raise VerificationError("Cannot read a supplied artifact file") from None


def verify(html_path: Path, receipt_path: Path, *, input_path: Path | None = None,
           research_path: Path | None = None, decisions_path: Path | None = None,
           require_profile: str | None = None) -> dict[str, Any]:
    """Check exact bytes and declared profile, without executing or rewriting artifacts."""
    if html_path is None:
        raise VerificationError("An HTML artifact file is required")
    if require_profile is not None and (not isinstance(require_profile, str) or require_profile not in PROFILES):
        raise VerificationError("Requested export profile is unsupported")
    receipt = load_receipt(receipt_path)
    validate_receipt(receipt)
    if require_profile is not None and receipt["export_profile"] != require_profile:
        raise VerificationError("Receipt export profile does not match the requested profile")
    checks = {}
    for label, path, key in (
        ("html", html_path, "html_sha256"),
        ("itinerary", input_path, "itinerary_sha256"),
        ("research", research_path, "research_sha256"),
        ("decisions", decisions_path, "decisions_sha256"),
    ):
        expected = receipt[key]
        if path is None:
            checks[label] = "not_recorded" if expected is None else "not_supplied"
        elif expected is None:
            raise VerificationError("A supplied artifact has no recorded digest")
        elif file_digest(path) != expected:
            raise VerificationError(f"The supplied {label} file does not match its recorded digest")
        else:
            checks[label] = "matched"
    return {
        "status": "match", "scope": "artifact_integrity", "receipt_binding": "matched",
        "export_profile": receipt["export_profile"], "checks": checks,
        "authenticity": "not_verified", "source_freshness": "not_checked",
    }


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, "Invalid verification arguments; use --help for the supported options\n")


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--input", type=Path, help="optional original itinerary JSON file")
    parser.add_argument("--research", type=Path, help="optional research state file")
    parser.add_argument("--decisions", type=Path, help="optional conflict decisions file")
    parser.add_argument("--require-profile", choices=sorted(PROFILES), help="require the receipt's declared export profile")
    args = parser.parse_args()
    try:
        result = verify(args.html, args.receipt, input_path=args.input, research_path=args.research,
                        decisions_path=args.decisions, require_profile=args.require_profile)
    except VerificationError as error:
        print(f"Verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
