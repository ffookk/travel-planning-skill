#!/usr/bin/env python3
"""Audit the exact final itinerary before publishing HTML and a bound receipt."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any


SPEC = importlib.util.spec_from_file_location("final_delivery_audit", Path(__file__).with_name("audit_itinerary.py"))
assert SPEC and SPEC.loader
audit_itinerary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_itinerary)


class FinalizationError(ValueError):
    """A final delivery was refused without publishing its artifacts."""


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def load_document(path: Path, label: str) -> tuple[dict[str, Any], str]:
    def reject_constant(_: str) -> None:
        raise ValueError

    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
        if not isinstance(value, dict):
            raise ValueError
    except (OSError, UnicodeError, ValueError):
        raise FinalizationError(f"Cannot read a valid {label} JSON object") from None
    return value, digest(raw)


def pointer_value(value: Any, pointer: str) -> Any:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise FinalizationError("Conflict decisions require an absolute JSON pointer")
    try:
        for part in pointer[1:].split("/"):
            if re.search(r"~(?![01])", part):
                raise ValueError
            key = part.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", key) else value[key]
        return value
    except (IndexError, KeyError, TypeError, ValueError):
        raise FinalizationError("A conflict decision pointer does not resolve in the itinerary") from None


def child_pointer(path: str, key: Any) -> str:
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def used_entities(data: dict[str, Any]) -> tuple[dict[str, set[str]], set[str], set[str]]:
    """Follow explicit references from published days into planning collections."""
    index: dict[str, list[tuple[str, dict[str, Any]]]] = {}

    def index_objects(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key in ("id", "entity_id"):
                if isinstance(value.get(key), str):
                    index.setdefault(value[key], []).append((path, value))
            for key, child in value.items():
                index_objects(child, child_pointer(path, key))
        elif isinstance(value, list):
            for i, child in enumerate(value):
                index_objects(child, child_pointer(path, i))

    index_objects(data.get("planning") or {}, "/planning")
    owners: dict[str, set[str]] = {}
    visited: set[str] = set()
    reachable_objects: set[str] = set()

    def visit(value: Any, path: str) -> None:
        if path in visited:
            return
        visited.add(path)
        if isinstance(value, dict):
            reachable_objects.add(path)
            for key, child in value.items():
                if key in {"id", "entity_id"} or key.endswith("_id") or key.endswith("_ids"):
                    references = child if isinstance(child, list) else [child]
                    for reference in references:
                        if not isinstance(reference, str):
                            continue
                        matches = index.get(reference) or []
                        if len({path for path, _ in matches}) > 1:
                            raise FinalizationError("A referenced planning identifier belongs to multiple objects")
                        if matches:
                            owners.setdefault(reference, set()).update(p for p, _ in matches)
                        else:
                            owners.setdefault(reference, set()).add(path)
                        for target_path, target in matches:
                            visit(target, target_path)
                visit(child, child_pointer(path, key))
        elif isinstance(value, list):
            for i, child in enumerate(value):
                visit(child, child_pointer(path, i))

    visit(data.get("days") or [], "/days")
    visit((data.get("planning") or {}).get("daily_routes") or [], "/planning/daily_routes")
    visit((data.get("planning") or {}).get("readiness") or [], "/planning/readiness")
    return owners, set(index), reachable_objects


def check_conflicts(data: dict[str, Any], research: dict[str, Any], decisions: dict[str, Any] | None,
                    input_sha: str, research_sha: str) -> dict[str, Any]:
    state = research.get("global_state")
    if research.get("schema_version") != "travel-research-state/v2" or not isinstance(state, dict):
        raise FinalizationError("Research state must use travel-research-state/v2 with global_state")
    conflicts = state.get("conflicts")
    if not isinstance(conflicts, list) or not all(isinstance(item, dict) for item in conflicts):
        raise FinalizationError("Research state must declare its conflicts array")
    owners, known_ids, reachable = used_entities(data)
    by_hash = {digest(canonical(item)): item for item in conflicts}
    group_values: dict[tuple[str, str], set[bytes]] = {}
    for conflict in conflicts:
        entity_id, field = conflict.get("entity_id"), conflict.get("field")
        if (not isinstance(entity_id, str) or not entity_id or not isinstance(field, str) or not field
                or "previous_value" not in conflict or "incoming_value" not in conflict):
            raise FinalizationError("Research conflict identity or recorded values are invalid")
        group_values.setdefault((entity_id, field), set()).update(
            canonical(conflict[name]) for name in ("previous_value", "incoming_value")
        )
    conflict_ids = {item.get("entity_id") for item in conflicts if isinstance(item.get("entity_id"), str)}
    if len(conflict_ids) == 0 and conflicts:
        raise FinalizationError("Research conflicts require entity identifiers")
    usage: dict[str, dict[str, Any]] = {}
    choices: dict[str, dict[str, Any]] = {}
    if decisions is not None:
        if (decisions.get("schema_version") != "itinerary-conflict-decisions/v1"
                or decisions.get("itinerary_sha256") != input_sha or decisions.get("research_sha256") != research_sha):
            raise FinalizationError("Conflict decisions are stale or use an unsupported schema")
        for field in ("entity_usage", "decisions"):
            if not isinstance(decisions.get(field, []), list):
                raise FinalizationError("Conflict usage and decisions must be arrays")
        for entry in decisions.get("entity_usage", []):
            if not isinstance(entry, dict) or entry.get("entity_id") not in conflict_ids:
                raise FinalizationError("Conflict usage must identify a current conflicting entity")
            entity_id = entry["entity_id"]
            if (entity_id in usage or entry.get("usage") not in {"used", "unused"}
                    or not isinstance(entry.get("reason"), str) or not entry["reason"].strip()):
                raise FinalizationError("Conflict usage requires one explicit classification and reason per entity")
            if entry["usage"] == "unused" and entity_id in owners:
                raise FinalizationError("A referenced entity cannot be declared unused")
            if entry["usage"] == "used":
                path = entry.get("itinerary_pointer")
                if path not in reachable or not isinstance(pointer_value(data, path), dict):
                    raise FinalizationError("Used entity mappings must point to a reachable itinerary object")
                if entity_id in owners and path not in owners[entity_id]:
                    raise FinalizationError("A used entity mapping cannot redefine a known itinerary identifier")
                owners.setdefault(entity_id, set()).add(path)
            usage[entity_id] = entry
        for entry in decisions.get("decisions", []):
            key = entry.get("conflict_sha256") if isinstance(entry, dict) else None
            if key not in by_hash or key in choices:
                raise FinalizationError("Conflict decisions must uniquely identify current conflicts")
            choices[key] = entry
    source_ids = {item.get("id") for item in data.get("sources") or [] if isinstance(item, dict)}
    resolved = unused = 0
    group_decisions: dict[tuple[str, str], tuple[bytes, str]] = {}
    for key, conflict in by_hash.items():
        entity_id = conflict.get("entity_id")
        if entity_id not in owners:
            if entity_id in known_ids or (usage.get(entity_id) or {}).get("usage") == "unused":
                if key in choices:
                    raise FinalizationError("Unused conflicts must not carry a used-value decision")
                unused += 1
                continue
            raise FinalizationError("A research conflict needs an explicit used or unused entity mapping")
        choice = choices.get(key)
        if (not choice or "selected_value" not in choice or not isinstance(choice.get("reason"), str)
                or not choice["reason"].strip()):
            raise FinalizationError("A used entity conflict requires an explicit value decision and reason")
        evidence = choice.get("source_ids")
        if not isinstance(evidence, list) or not evidence or any(not isinstance(s, str) or s not in source_ids for s in evidence):
            raise FinalizationError("Conflict decisions require source IDs registered in the itinerary")
        selected = canonical(choice["selected_value"])
        group = (entity_id, conflict["field"])
        if selected not in group_values[group]:
            raise FinalizationError("A conflict decision must select a value recorded for this field; re-merge new evidence first")
        pointer = choice.get("itinerary_pointer")
        field_parts = conflict["field"].split(".")
        if not all(field_parts):
            raise FinalizationError("Conflict fields must use a nonempty dot path")
        expected_paths = set()
        for owner in owners[entity_id]:
            parts = field_parts
            if parts == ["canonical_name"] and "name" in pointer_value(data, owner):
                parts = ["name"]
            elif parts[0] == "facts" and len(parts) > 1:
                flattened = owner
                for part in parts[1:]:
                    flattened = child_pointer(flattened, part)
                try:
                    pointer_value(data, flattened)
                except FinalizationError:
                    pass
                else:
                    parts = parts[1:]
            expected = owner
            for part in parts:
                expected = child_pointer(expected, part)
            expected_paths.add(expected)
        if pointer not in expected_paths:
            raise FinalizationError("Conflict decision pointers must match the conflicted field on the used entity")
        selection = (selected, pointer)
        if group in group_decisions and group_decisions[group] != selection:
            raise FinalizationError("All conflicts for one entity field must share the final value and pointer")
        group_decisions[group] = selection
        if canonical(pointer_value(data, pointer)) != selected:
            raise FinalizationError("The decided conflict value does not match the final itinerary")
        resolved += 1
    return {"status": "checked", "resolved_conflict_count": resolved, "unused_conflict_count": unused}


def publish(artifacts: list[tuple[Path, bytes]]) -> None:
    """Stage complete files, replace atomically, and roll back ordinary I/O failures."""
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path | None] = {}
    original_modes: dict[Path, int] = {}
    replaced: list[Path] = []
    rollback_failed = False

    def stage(target: Path, content: bytes) -> Path:
        descriptor, name = tempfile.mkstemp(prefix=".final-delivery-", dir=target.parent)
        path = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return path

    try:
        for target, content in artifacts:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise FinalizationError("Delivery targets must be regular files, not symlinks or directories")
            if target.exists():
                if os.name == "posix":
                    original_modes[target] = stat.S_IMODE(target.stat().st_mode)
                backups[target] = stage(target, target.read_bytes())
            else:
                backups[target] = None
            staged[target] = stage(target, content)
        for target, _ in artifacts:
            os.replace(staged[target], target)
            replaced.append(target)
    except (OSError, FinalizationError):
        try:
            for target in reversed(replaced):
                if backups[target] is None:
                    target.unlink(missing_ok=True)
                elif os.name == "posix":
                    with backups[target].open("rb") as original:
                        os.replace(backups[target], target)
                        # Widen only the restored original, never a staged backup or new delivery.
                        os.fchmod(original.fileno(), original_modes[target])
                else:
                    os.replace(backups[target], target)
        except OSError:
            rollback_failed = True
            raise FinalizationError("Publication and rollback failed; recovery backups remain beside delivery targets; check them locally before using any delivery") from None
        raise FinalizationError("Final delivery could not be published; previous outputs were preserved") from None
    finally:
        cleanup = [*staged.values(), *([] if rollback_failed else backups.values())]
        for path in cleanup:
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass


def finalize(input_path: Path, output_path: Path, report_path: Path, *, workspace: Path | None = None,
             research_sha256: str | None = None, decisions_path: Path | None = None,
             private_offline: bool = False) -> dict[str, Any]:
    data, input_sha = load_document(input_path, "itinerary")
    workflow, planning = data.get("workflow"), data.get("planning")
    if not isinstance(workflow, dict) or workflow.get("phase") != "final" or not isinstance(planning, dict) or not planning.get("readiness"):
        raise FinalizationError("Final delivery requires workflow.phase=final and planning.readiness; use the renderer for drafts")
    context = data.get("research_context")
    if context is not None and (not isinstance(context, dict) or context.get("schema_version") != "itinerary-research-context/v1"
                                or not re.fullmatch(r"[a-f0-9]{64}", str(context.get("research_state_sha256") or ""))):
        raise FinalizationError("Itinerary research provenance is invalid")
    if (context is not None or research_sha256 is not None or decisions_path is not None) and workspace is None:
        raise FinalizationError("Research-based final delivery requires --workspace")
    research_sha = decisions_sha = None
    conflict_summary = {"status": "conflicts_not_checked"}
    protected = [input_path]
    if workspace is not None:
        root = workspace.resolve()
        research_path = (root / "state" / "research.json").resolve()
        if not research_path.is_relative_to(root):
            raise FinalizationError("Research state must resolve inside the workspace")
        research, research_sha = load_document(research_path, "research state")
        protected.append(research_path)
        for expected in (research_sha256, (context or {}).get("research_state_sha256")):
            if expected is not None and expected != research_sha:
                raise FinalizationError("Research state changed; reassemble before final delivery")
        decisions = None
        if decisions_path is not None:
            decisions, decisions_sha = load_document(decisions_path, "conflict decisions")
            protected.append(decisions_path)
        try:
            conflict_summary = check_conflicts(data, research, decisions, input_sha, research_sha)
        except (TypeError, KeyError, ValueError) as error:
            if isinstance(error, FinalizationError):
                raise
            raise FinalizationError("Research conflicts or decisions have an invalid structure") from None
    destinations = [output_path.resolve(), report_path.resolve()]
    if len(set(destinations)) != 2 or set(destinations).intersection(path.resolve() for path in protected):
        raise FinalizationError("Delivery outputs must be distinct from each other and all input files")
    builder = audit_itinerary.render_itinerary.build
    if private_offline:
        try:
            parameter = inspect.signature(builder).parameters.get("private_offline")
        except (TypeError, ValueError):
            parameter = None
        if parameter is None or parameter.kind not in {inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD}:
            raise FinalizationError("The requested private offline profile is unsupported by this renderer; no delivery was published")
    try:
        before = canonical(data)
        result = audit_itinerary.audit(data)
        if result.get("status") != "pass" or result.get("blocking"):
            raise FinalizationError("Audit found blocking issues; run audit_itinerary.py locally for details")
        html = (builder(data, private_offline=True) if private_offline else builder(data)).encode("utf-8")
        if canonical(data) != before:
            raise FinalizationError("Audit or rendering changed the loaded itinerary")
    except (ValueError, TypeError, KeyError, OverflowError) as error:
        if isinstance(error, FinalizationError):
            raise
        raise FinalizationError("Audit or rendering could not validate this itinerary; no delivery was published") from None
    binding = {"itinerary_sha256": input_sha, "html_sha256": digest(html), "research_sha256": research_sha,
               "decisions_sha256": decisions_sha, "export_profile": "private-offline" if private_offline else "regular"}
    report = {"schema_version": "itinerary-final-delivery/v1", "status": "pass", **binding,
              "binding_sha256": digest(canonical(binding)), "checked_at": result.get("checked_at"),
              "warning_count": len(result.get("warnings") or []), "checked_event_count": len(result.get("checked_event_ids") or []),
              "conflicts": conflict_summary}
    publish([(report_path, canonical(report) + b"\n"), (output_path, html)])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path, help="default: OUTPUT.final-audit.json")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--research-sha256", help="optional expected SHA256 of state/research.json")
    parser.add_argument("--conflict-decisions", type=Path)
    parser.add_argument("--private-offline", action="store_true", help="require an offline-capable renderer; never fall back to a regular export")
    args = parser.parse_args()
    try:
        report = finalize(args.input, args.output, args.report or args.output.with_name(args.output.name + ".final-audit.json"),
                          workspace=args.workspace, research_sha256=args.research_sha256, decisions_path=args.conflict_decisions,
                          private_offline=args.private_offline)
    except FinalizationError as error:
        print(f"Final delivery refused: {error}", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        print("Final delivery refused: an input or I/O operation failed", file=sys.stderr)
        return 1
    print(f"Final delivery passed. Binding SHA256: {report['binding_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
