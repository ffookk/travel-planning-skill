from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "travel_library", ROOT / "skills" / "travel-planning" / "scripts" / "travel_library.py"
)
assert SPEC and SPEC.loader
travel_library = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(travel_library)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


class TravelLibraryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.library = self.root / "library"
        travel_library.init_command(Namespace(root=str(self.library)))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def candidate(self) -> dict:
        return {
            "entity_id": "attraction-west-lake",
            "entity_type": "attraction",
            "canonical_name": "西湖风景名胜区",
            "aliases": ["西湖"],
            "tags": ["hangzhou", "lake"],
            "location": {"city": "杭州", "coordinates": "120.15,30.25"},
            "reusable": {
                "official_endpoints": {"homepage_url": "https://example.com/west-lake"},
                "entrances": [{"name": "湖滨公园入口", "coordinates": "120.15,30.25"}],
                "checkpoint_blueprint": [{"name": "湖滨", "kind": "visit"}],
                "typical_visit_duration": "约2小时"
            },
            "seasonal_profiles": [{"season": "autumn", "notes": ["清晨湖岸光线较柔和"]}],
            "verification_hints": ["每次行程重新查询开放、票价与临时公告"],
            "source_refs": [{
                "source_id": "library-west-lake-official",
                "title": "西湖官方入口",
                "url": "https://example.com/west-lake",
                "kind": "official",
                "authority": "attraction_operator",
                "last_verified_at": "2026-09-20T10:00:00+08:00",
                "status": "active"
            }],
        }

    def restaurant_candidate(self) -> dict:
        return {
            "entity_id": "restaurant-hangzhou-demo",
            "entity_type": "restaurant",
            "entity_schema_version": 2,
            "canonical_name": "杭州示例餐厅",
            "aliases": [],
            "tags": ["hangzhou", "restaurant"],
            "location": {"city": "杭州"},
            "reusable": {
                "physical_address": "浙江省杭州市西湖区示例路1号",
                "coordinates": "120.100000,30.200000",
                "amap_poi_id": "demo-poi-id",
                "official_endpoints": {"amap": "https://www.amap.com/place/demo"},
                "signature_dishes": ["片儿川"],
                "cuisine": ["杭帮菜"],
                "image_refs": [{
                    "kind": "link_preview",
                    "source_url": "https://example.com/restaurant-gallery",
                    "alt": "查看餐厅相册",
                    "source_label": "商家页面",
                    "checked_at": "2026-09-21T10:00:00+08:00",
                }],
            },
            "source_refs": [{
                "source_id": "restaurant-amap-demo",
                "title": "地图详情",
                "url": "https://www.amap.com/place/demo",
                "kind": "map",
                "authority": "map_provider",
                "last_verified_at": "2026-09-21T10:00:00+08:00",
                "status": "active",
            }],
        }

    def test_stores_searches_and_versions_reusable_entity(self) -> None:
        source = self.root / "entity.json"
        write_json(source, self.candidate())
        created = travel_library.upsert(Namespace(root=str(self.library), entity_file=str(source), expected_revision=None))
        self.assertEqual(created["revision"], 1)
        found = travel_library.search(Namespace(root=str(self.library), query="西湖", entity_type=None, location="杭州", tag=None, limit=20))
        self.assertEqual(found["match_count"], 1)
        with self.assertRaisesRegex(travel_library.LibraryError, "expected-revision"):
            travel_library.upsert(Namespace(root=str(self.library), entity_file=str(source), expected_revision=None))
        updated = travel_library.upsert(Namespace(root=str(self.library), entity_file=str(source), expected_revision=1))
        self.assertEqual(updated["revision"], 2)
        self.assertTrue((self.library / "history" / "attraction" / "attraction-west-lake" / "1.json").is_file())

    def test_rejects_dynamic_fact_inside_reusable_core(self) -> None:
        candidate = self.candidate()
        candidate["reusable"]["opening_hours"] = "08:00-18:00"
        source = self.root / "bad.json"
        write_json(source, candidate)
        with self.assertRaisesRegex(travel_library.LibraryError, "未允许字段"):
            travel_library.upsert(Namespace(root=str(self.library), entity_file=str(source), expected_revision=None))

    def test_restaurant_entity_keeps_only_stable_fields_and_schema_version(self) -> None:
        source = self.root / "restaurant.json"
        write_json(source, self.restaurant_candidate())
        created = travel_library.upsert(Namespace(root=str(self.library), entity_file=str(source), expected_revision=None))
        stored = json.loads(Path(created["path"]).read_text(encoding="utf-8"))
        self.assertEqual(stored["entity_schema_version"], 2)
        self.assertEqual(stored["reusable"]["amap_poi_id"], "demo-poi-id")
        self.assertNotIn("rating", stored["reusable"])

    def test_restaurant_entity_rejects_dynamic_rating(self) -> None:
        candidate = self.restaurant_candidate()
        candidate["reusable"]["rating"] = "4.8"
        with self.assertRaisesRegex(travel_library.LibraryError, "未允许字段|动态字段"):
            travel_library.validate_candidate(candidate)

    def test_restaurant_entity_requires_visual_source(self) -> None:
        candidate = self.restaurant_candidate()
        candidate["reusable"]["image_refs"] = []
        with self.assertRaisesRegex(travel_library.LibraryError, "缺少稳定字段"):
            travel_library.validate_candidate(candidate)

    def test_materializes_versioned_seed_into_trip_workspace(self) -> None:
        source = self.root / "entity.json"
        write_json(source, self.candidate())
        travel_library.upsert(Namespace(root=str(self.library), entity_file=str(source), expected_revision=None))
        workspace = self.root / "trip"
        (workspace / "state").mkdir(parents=True)
        write_json(workspace / "manifest.json", {"shared_library": {"root": str(self.library)}})
        result = travel_library.materialize(Namespace(workspace=str(workspace), root=None, entity_id=["attraction-west-lake"], include_stale=False))
        self.assertEqual(result["entity_count"], 1)
        seed = json.loads((workspace / "state" / "library-seed.json").read_text(encoding="utf-8"))
        self.assertEqual(seed["entities"][0]["catalog_revision"], 1)
        self.assertEqual(seed["entities"][0]["entity"]["canonical_name"], "西湖风景名胜区")

    def test_materialize_rejects_stale_entity_by_default(self) -> None:
        candidate = self.candidate()
        candidate["review_after"] = "2020-01-01T00:00:00+08:00"
        source = self.root / "stale.json"
        write_json(source, candidate)
        travel_library.upsert(Namespace(root=str(self.library), entity_file=str(source), expected_revision=None))
        workspace = self.root / "trip"
        (workspace / "state").mkdir(parents=True)
        write_json(workspace / "manifest.json", {"shared_library": {"root": str(self.library)}})
        with self.assertRaisesRegex(travel_library.LibraryError, "不可直接复用"):
            travel_library.materialize(Namespace(workspace=str(workspace), root=None, entity_id=["attraction-west-lake"], include_stale=False))

    def test_main_agent_can_promote_reviewed_candidate(self) -> None:
        workspace = self.root / "trip"
        (workspace / "results").mkdir(parents=True)
        (workspace / "state").mkdir()
        write_json(workspace / "manifest.json", {"shared_library": {"root": str(self.library)}})
        write_json(workspace / "results" / "attractions.json", {"catalog_candidates": [self.candidate()]})
        result = travel_library.promote(Namespace(
            workspace=str(workspace), task_id="attractions", entity_id="attraction-west-lake", root=None, expected_revision=None
        ))
        self.assertEqual(result["status"], "promoted")
        promotions = json.loads((workspace / "state" / "library-promotions.json").read_text(encoding="utf-8"))
        self.assertEqual(promotions["promotions"][0]["entity_id"], "attraction-west-lake")


if __name__ == "__main__":
    unittest.main()
