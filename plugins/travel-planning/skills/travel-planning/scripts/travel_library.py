#!/usr/bin/env python3
"""Manage reusable travel entities outside any single trip workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


LIBRARY_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,95}$")
ENTITY_TYPES = {"attraction", "place", "transport_hub", "lodging", "restaurant", "route_anchor"}
REUSABLE_FIELDS = {
    "attraction": {"official_endpoints", "entrances", "exits", "checkpoint_blueprint", "typical_visit_duration", "accessibility", "image_refs"},
    "place": {"physical_address", "coordinates", "official_endpoints", "accessibility", "image_refs"},
    "transport_hub": {"physical_address", "coordinates", "official_endpoints", "access_points", "facilities"},
    "lodging": {"physical_address", "coordinates", "official_endpoints", "facilities", "luggage_storage_policy"},
    "restaurant": {
        "physical_address", "coordinates", "amap_poi_id", "other_platform_ids",
        "phone", "official_endpoints", "signature_dishes", "cuisine",
        "meal_types", "service_modes", "dietary_tags", "facilities",
        "parking_profile", "inside_attraction", "image_refs",
    },
    "route_anchor": {"coordinates", "entrance_or_exit_name", "access_modes", "location_query"},
}
ENTITY_STATUSES = {"active", "needs_review", "deprecated", "superseded"}
SOURCE_STATUSES = {"active", "invalid", "superseded"}
RESTAURANT_REQUIRED_REUSABLE_FIELDS = {
    "physical_address", "coordinates", "amap_poi_id", "signature_dishes",
    "cuisine", "official_endpoints", "image_refs",
}
RESTAURANT_DYNAMIC_FIELDS = {
    "rating", "review_count", "per_person", "opening_hours", "queue",
    "reservation", "current_price", "current_menu", "distance",
    "duration", "detour_minutes", "xiaohongshu_interactions",
}


class LibraryError(RuntimeError):
    """The shared library operation violates its version or reuse contract."""


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise LibraryError(f"文件不存在：{path}") from error
    except json.JSONDecodeError as error:
        raise LibraryError(f"JSON 无效：{path}: {error}") from error


def atomic_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def digest(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def library_root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def initialize(root: Path) -> None:
    (root / "entities").mkdir(parents=True, exist_ok=True)
    manifest = root / "manifest.json"
    if not manifest.exists():
        atomic_write(manifest, {"library_version": LIBRARY_VERSION, "created_at": now()})
        return
    payload = read_json(manifest)
    if payload.get("library_version") != LIBRARY_VERSION:
        raise LibraryError(f"不支持的公共资料库版本：{payload.get('library_version')}")


def valid_id(value: str) -> str:
    if not ID_PATTERN.fullmatch(value):
        raise LibraryError("entity_id 只能使用小写字母、数字、下划线和连字符，最长 96 字符")
    return value


def validate_candidate(candidate: dict[str, Any]) -> None:
    required = {"entity_id", "entity_type", "canonical_name", "reusable", "source_refs"}
    missing = sorted(field for field in required if field not in candidate or candidate.get(field) in (None, ""))
    if missing:
        raise LibraryError(f"公共实体候选缺少字段：{', '.join(missing)}")
    valid_id(str(candidate["entity_id"]))
    if candidate["entity_type"] not in ENTITY_TYPES:
        raise LibraryError(f"entity_type 无效：{candidate['entity_type']}")
    if not isinstance(candidate["reusable"], dict) or not isinstance(candidate["source_refs"], list):
        raise LibraryError("reusable 必须是对象，source_refs 必须是数组")
    unknown = sorted(set(candidate["reusable"]) - REUSABLE_FIELDS[candidate["entity_type"]])
    if unknown:
        raise LibraryError(f"公共实体 reusable 包含未允许字段：{', '.join(unknown)}")
    if candidate["entity_type"] == "restaurant":
        reusable = candidate["reusable"]
        dynamic = sorted(set(reusable) & RESTAURANT_DYNAMIC_FIELDS)
        if dynamic:
            raise LibraryError(f"餐厅公共实体不得保存动态字段：{', '.join(dynamic)}")
        missing_restaurant = sorted(
            field for field in RESTAURANT_REQUIRED_REUSABLE_FIELDS
            if field not in reusable or reusable.get(field) in (None, "", [], {})
        )
        if missing_restaurant:
            raise LibraryError(f"餐厅公共实体缺少稳定字段：{', '.join(missing_restaurant)}")
        if not isinstance(reusable.get("signature_dishes"), list) or not isinstance(reusable.get("cuisine"), list):
            raise LibraryError("餐厅 signature_dishes 和 cuisine 必须是数组")
        endpoints = reusable.get("official_endpoints") or {}
        if not isinstance(endpoints, dict) or not any(str(value).startswith("https://") for value in endpoints.values()):
            raise LibraryError("餐厅 official_endpoints 至少包含一个 HTTPS 官方或稳定平台详情入口")
        for index, image in enumerate(reusable.get("image_refs") or []):
            if not isinstance(image, dict):
                raise LibraryError(f"餐厅 image_refs[{index}] 必须是对象")
            required_image = {"kind", "source_url", "alt", "source_label", "checked_at"}
            missing_image = sorted(field for field in required_image if not image.get(field))
            if missing_image:
                raise LibraryError(f"餐厅 image_refs[{index}] 缺少字段：{', '.join(missing_image)}")
            if not str(image["source_url"]).startswith("https://"):
                raise LibraryError(f"餐厅 image_refs[{index}].source_url 必须使用 HTTPS")
            if image["kind"] == "display_image":
                display_required = {"url", "author", "license_or_permission"}
                missing_display = sorted(field for field in display_required if not image.get(field))
                if missing_display:
                    raise LibraryError(f"餐厅 image_refs[{index}] 可展示图片缺少字段：{', '.join(missing_display)}")
                if not str(image["url"]).startswith("https://"):
                    raise LibraryError(f"餐厅 image_refs[{index}].url 必须使用 HTTPS")
            elif image["kind"] != "link_preview":
                raise LibraryError(f"餐厅 image_refs[{index}].kind 只能是 display_image 或 link_preview")
    for index, source in enumerate(candidate["source_refs"]):
        required_source = {"source_id", "title", "url", "kind", "authority", "last_verified_at", "status"}
        if not isinstance(source, dict):
            raise LibraryError(f"source_refs[{index}] 必须是对象")
        missing_source = sorted(field for field in required_source if not source.get(field))
        if missing_source:
            raise LibraryError(f"source_refs[{index}] 缺少字段：{', '.join(missing_source)}")
        if not str(source["url"]).startswith("https://"):
            raise LibraryError(f"source_refs[{index}] 必须提供 HTTPS url")
        if source["status"] not in SOURCE_STATUSES:
            raise LibraryError(f"source_refs[{index}].status 无效")


def entity_path(root: Path, entity_type: str, entity_id: str) -> Path:
    return root / "entities" / entity_type / f"{entity_id}.json"


def init_command(args: argparse.Namespace) -> dict[str, Any]:
    root = library_root(args.root)
    initialize(root)
    return {"status": "ready", "root": str(root), "library_version": LIBRARY_VERSION}


def upsert(args: argparse.Namespace) -> dict[str, Any]:
    root = library_root(args.root)
    initialize(root)
    candidate = read_json(Path(args.entity_file).expanduser().resolve())
    if not isinstance(candidate, dict):
        raise LibraryError("--entity-file 必须是 JSON 对象")
    validate_candidate(candidate)
    target = entity_path(root, candidate["entity_type"], valid_id(str(candidate["entity_id"])))
    existing = read_json(target) if target.exists() else None
    if existing:
        if args.expected_revision is None:
            raise LibraryError("实体已存在；更新时必须提供 --expected-revision")
        if existing.get("revision") != args.expected_revision:
            raise LibraryError(f"版本冲突：当前 revision={existing.get('revision')}")
        revision = int(existing["revision"]) + 1
        created_at = existing.get("created_at")
        history = root / "history" / str(existing["entity_type"]) / str(existing["entity_id"]) / f'{existing["revision"]}.json'
        atomic_write(history, existing)
    else:
        if args.expected_revision is not None:
            raise LibraryError("新实体不应提供 --expected-revision")
        revision = 1
        created_at = now()
    record = {
        "library_version": LIBRARY_VERSION,
        "entity_id": candidate["entity_id"],
        "entity_type": candidate["entity_type"],
        "canonical_name": candidate["canonical_name"],
        "aliases": candidate.get("aliases") or [],
        "tags": candidate.get("tags") or [],
        "location": candidate.get("location") or {},
        "reusable": candidate["reusable"],
        "seasonal_profiles": candidate.get("seasonal_profiles") or [],
        "verification_hints": candidate.get("verification_hints") or [],
        "source_refs": candidate["source_refs"],
        "entity_schema_version": int(candidate.get("entity_schema_version") or 1),
        "status": candidate.get("status") or "active",
        "last_verified_at": candidate.get("last_verified_at") or max(str(item["last_verified_at"]) for item in candidate["source_refs"]),
        "review_after": candidate.get("review_after"),
        "superseded_by": candidate.get("superseded_by"),
        "revision": revision,
        "created_at": created_at,
        "updated_at": now(),
    }
    if record["status"] not in ENTITY_STATUSES:
        raise LibraryError(f"实体 status 无效：{record['status']}")
    record["content_digest"] = digest({key: value for key, value in record.items() if key not in {"updated_at", "content_digest"}})
    atomic_write(target, record)
    return {"status": "stored", "root": str(root), "entity_id": record["entity_id"], "revision": revision, "path": str(target)}


def iter_entities(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    initialize(root)
    rows = []
    for path in sorted((root / "entities").glob("*/*.json")):
        value = read_json(path)
        if not isinstance(value, dict):
            raise LibraryError(f"公共实体必须是 JSON 对象：{path}")
        rows.append((path, value))
    return rows


def search(args: argparse.Namespace) -> dict[str, Any]:
    root = library_root(args.root)
    terms = [term.casefold() for term in (args.query or "").split() if term]
    matches = []
    for path, record in iter_entities(root):
        if args.entity_type and record.get("entity_type") != args.entity_type:
            continue
        if args.tag and args.tag not in (record.get("tags") or []):
            continue
        if args.location and args.location.casefold() not in json.dumps(record.get("location") or {}, ensure_ascii=False).casefold():
            continue
        haystack = json.dumps({key: record.get(key) for key in ("canonical_name", "aliases", "tags", "location", "reusable")}, ensure_ascii=False).casefold()
        if terms and not all(term in haystack for term in terms):
            continue
        stale = is_stale(record)
        matches.append({
            "entity_id": record.get("entity_id"),
            "entity_type": record.get("entity_type"),
            "canonical_name": record.get("canonical_name"),
            "revision": record.get("revision"),
            "content_digest": record.get("content_digest"),
            "status": record.get("status"),
            "stale": stale,
            "path": str(path),
        })
    return {"status": "ok", "root": str(root), "match_count": len(matches[:args.limit]), "matches": matches[:args.limit]}


def is_stale(record: dict[str, Any]) -> bool:
    review_after = record.get("review_after")
    if not review_after:
        return False
    try:
        return datetime.fromisoformat(str(review_after)) < datetime.now().astimezone()
    except ValueError:
        return True


def materialize(args: argparse.Namespace) -> dict[str, Any]:
    workspace = Path(args.workspace).expanduser().resolve()
    manifest_path = workspace / "manifest.json"
    if not manifest_path.is_file():
        raise LibraryError(f"不是有效研究工作区：{workspace}")
    manifest = read_json(manifest_path)
    root = library_root(args.root or manifest.get("shared_library", {}).get("root") or ".travel-library")
    records = {record.get("entity_id"): (path, record) for path, record in iter_entities(root)}
    selected = []
    for entity_id in args.entity_id or []:
        if entity_id not in records:
            raise LibraryError(f"公共实体不存在：{entity_id}")
        path, record = records[entity_id]
        if not getattr(args, "include_stale", False) and (record.get("status") != "active" or is_stale(record)):
            raise LibraryError(f"公共实体不可直接复用：{entity_id} status={record.get('status')} stale={is_stale(record)}")
        selected.append({"catalog_path": str(path), "catalog_revision": record.get("revision"), "content_digest": record.get("content_digest"), "entity": record})
    seed = {"library_version": LIBRARY_VERSION, "library_root": str(root), "materialized_at": now(), "entities": selected}
    target = workspace / "state" / "library-seed.json"
    atomic_write(target, seed)
    return {"status": "materialized", "workspace": str(workspace), "entity_count": len(selected), "path": str(target)}


def promote(args: argparse.Namespace) -> dict[str, Any]:
    workspace = Path(args.workspace).expanduser().resolve()
    manifest = read_json(workspace / "manifest.json")
    root = library_root(args.root or manifest.get("shared_library", {}).get("root") or ".travel-library")
    result = read_json(workspace / "results" / f"{args.task_id}.json")
    candidates = result.get("catalog_candidates") or []
    candidate = next((item for item in candidates if item.get("entity_id") == args.entity_id), None)
    if not candidate:
        raise LibraryError(f"任务 {args.task_id} 未提交公共候选：{args.entity_id}")
    temporary = workspace / "state" / f".promote-{args.entity_id}.json"
    atomic_write(temporary, candidate)
    try:
        stored = upsert(argparse.Namespace(root=str(root), entity_file=str(temporary), expected_revision=args.expected_revision))
    finally:
        if temporary.exists():
            temporary.unlink()
    promotion_file = workspace / "state" / "library-promotions.json"
    promotion_state = read_json(promotion_file) if promotion_file.exists() else {"promotions": []}
    promotion_state["promotions"].append({
        "entity_id": args.entity_id,
        "task_id": args.task_id,
        "revision": stored["revision"],
        "content_digest": read_json(Path(stored["path"]))["content_digest"],
        "promoted_at": now(),
    })
    atomic_write(promotion_file, promotion_state)
    return {**stored, "status": "promoted", "workspace": str(workspace)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    command = subparsers.add_parser("init", help="初始化跨行程公共资料库")
    command.add_argument("--root", default=".travel-library")
    command.set_defaults(handler=init_command)

    command = subparsers.add_parser("upsert", help="以乐观版本锁创建或更新公共实体")
    command.add_argument("--root", default=".travel-library")
    command.add_argument("--entity-file", required=True)
    command.add_argument("--expected-revision", type=int)
    command.set_defaults(handler=upsert)

    command = subparsers.add_parser("search", help="搜索可复用公共实体")
    command.add_argument("--root", default=".travel-library")
    command.add_argument("--query")
    command.add_argument("--entity-type", choices=sorted(ENTITY_TYPES))
    command.add_argument("--location")
    command.add_argument("--tag")
    command.add_argument("--limit", type=int, default=20, choices=range(1, 101), metavar="1-100")
    command.set_defaults(handler=search)

    command = subparsers.add_parser("materialize", help="把指定公共实体按版本快照到单次旅行")
    command.add_argument("--workspace", required=True)
    command.add_argument("--root")
    command.add_argument("--entity-id", action="append", required=True)
    command.add_argument("--include-stale", action="store_true", help="仅用于审计，允许载入需复核或已过期实体")
    command.set_defaults(handler=materialize)

    command = subparsers.add_parser("promote", help="主 Agent 审核后把任务候选晋升到公共资料库")
    command.add_argument("--workspace", required=True)
    command.add_argument("--task-id", required=True)
    command.add_argument("--entity-id", required=True)
    command.add_argument("--root")
    command.add_argument("--expected-revision", type=int)
    command.set_defaults(handler=promote)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        print(json.dumps(args.handler(args), ensure_ascii=False, indent=2))
        return 0
    except LibraryError as error:
        print(json.dumps({"status": "error", "message": str(error), "checked_at": now()}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
