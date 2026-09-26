from __future__ import annotations

import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills" / "travel-planning"
MODULE_PATH = SKILL_ROOT / "scripts" / "render_itinerary.py"
SPEC = importlib.util.spec_from_file_location("render_offline_itinerary", MODULE_PATH)
assert SPEC and SPEC.loader
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


def media_fixture() -> dict:
    """Add synthetic media to the public example's validated research structure."""
    data = json.loads((SKILL_ROOT / "assets" / "example-itinerary.json").read_text(encoding="utf-8"))
    event = next(event for day in data["days"] for event in day["events"] if event.get("attraction_id") == "a1")
    event["images"] = [{
        "url": "https://images.example.test/event.jpg?signature=keep%2Fthis&token=a%2Bb",
        "alt": 'Event image <view> & "details"',
        "source_url": "https://sources.example.test/event?signature=keep%2Fthis&token=a%2Bb#origin",
        "source_label": "Event source", "author": "Event photographer", "license": "CC BY 4.0",
    }]
    event["execution"]["checkpoints"][0]["images"] = [{
        "url": "https://images.example.test/checkpoint.jpg?signature=keep%2Fthis&token=a%2Bb",
        "alt": "Checkpoint entrance image", "source_label": "Checkpoint source",
        "author": "Checkpoint photographer", "license": "CC0",
    }]
    event["community_refs"] = [{
        "source_url": "https://community.example.test/post?signature=keep%2Fthis&token=a%2Bb",
        "title": "Community walking notes", "author": "Community writer", "reason": "Entrance details",
    }]
    data["planning"]["attractions"][0]["official"]["wechat"] = {
        "account_name": "Example account & bookings", "menu_path": "Visit > Reserve",
        "checked_at": "2026-09-20",
    }
    data["planning"]["restaurants"][0]["media"] = [{
        "kind": "display_image", "url": "https://images.example.test/restaurant.jpg?token=synthetic",
        "alt": "Restaurant entrance image", "source_url": "https://sources.example.test/restaurant",
        "source_label": "Restaurant source", "author": "Restaurant photographer",
        "license_or_permission": "Permission granted", "checked_at": "2026-09-20",
    }]
    return data


class Document(HTMLParser):
    def __init__(self, document: str) -> None:
        super().__init__()
        self.elements: list[tuple[str, dict[str, str | None]]] = []
        self.text: list[str] = []
        self.feed(document)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements.append((tag, dict(attrs)))

    def handle_data(self, data: str) -> None:
        self.text.append(data)

    @property
    def links(self) -> set[str]:
        return {attrs["href"] for tag, attrs in self.elements if tag == "a" and attrs.get("href")}


class PrivateOfflineExportTest(unittest.TestCase):
    def test_default_export_remains_opt_in(self) -> None:
        data = media_fixture()
        original = renderer.build(data)
        self.assertEqual(original, renderer.build(data, private_offline=False))
        document = Document(original)
        self.assertTrue(any(tag == "script" for tag, _ in document.elements))
        self.assertEqual(sum(tag == "img" for tag, _ in document.elements), 3)
        self.assertTrue(any(tag == "iframe" and attrs.get("data-src") for tag, attrs in document.elements))
        self.assertNotIn('data-export-profile="private-offline"', original)
        self.assertNotIn('http-equiv="Content-Security-Policy"', original)

    def test_offline_export_removes_all_automatic_media_and_scripts(self) -> None:
        result = renderer.build(media_fixture(), private_offline=True)
        document = Document(result)
        for tag, attrs in document.elements:
            self.assertNotIn(tag, {"script", "img", "iframe", "object", "embed", "audio", "video", "source", "track", "link", "base"})
            self.assertFalse({"src", "srcset", "data-src", "data-mobile-src", "poster", "background", "ping", "srcdoc"}.intersection(attrs))
            self.assertFalse(any(name.startswith("on") for name in attrs))
            for name, value in attrs.items():
                if (value or "").startswith(("https://", "http://", "//")):
                    self.assertEqual((tag, name), ("a", "href"))
        policies = [attrs["content"] for tag, attrs in document.elements if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy"]
        self.assertEqual(len(policies), 1)
        for directive in ("default-src 'none'", "script-src 'none'", "img-src 'none'", "frame-src 'none'", "connect-src 'none'", "style-src 'unsafe-inline'"):
            self.assertIn(directive, policies[0])
        self.assertLess(result.index("Content-Security-Policy"), result.index("<style>"))
        self.assertNotIn("url(", result)
        self.assertNotIn("@import", result)

    def test_offline_export_preserves_itinerary_context_and_intentional_links(self) -> None:
        data = media_fixture()
        original = Document(renderer.build(data))
        document = Document(renderer.build(data, private_offline=True))
        self.assertTrue(original.links.issubset(document.links))
        self.assertIn("https://sources.example.test/event?signature=keep%2Fthis&token=a%2Bb#origin", document.links)
        self.assertIn("https://images.example.test/checkpoint.jpg?signature=keep%2Fthis&token=a%2Bb", document.links)
        text = " ".join(document.text)
        for value in (
            data["trip"]["title"], 'Event image <view> & "details"', "Event photographer", "CC BY 4.0",
            "Checkpoint entrance image", "Checkpoint photographer", "CC0", "Restaurant entrance image",
            "Restaurant photographer", "Permission granted", "Community walking notes", "Community writer",
            "Example account & bookings", "Visit > Reserve", "not anonymized or made safe to share",
        ):
            self.assertIn(value, text)
        for day in data["days"]:
            for event in day["events"]:
                self.assertIn(event["title"], text)
                self.assertIn(event["time"], text)
                execution = event.get("execution") or {}
                for endpoint in (execution.get("entry"), execution.get("exit")):
                    if endpoint:
                        self.assertIn(endpoint["name"], text)
                for checkpoint in execution.get("checkpoints") or []:
                    self.assertIn(checkpoint["instruction"], text)
        for route in data["planning"]["daily_routes"]:
            for stop in route["stops"]:
                self.assertIn(stop["name"], text)
        self.assertFalse(any(tag == "button" for tag, _ in document.elements))
        self.assertNotIn("首次打开若出现登录提示", text)

    def test_offline_export_retains_native_view_switching_and_details(self) -> None:
        document = Document(renderer.build(media_fixture(), private_offline=True))
        ids = {attrs["id"] for _, attrs in document.elements if attrs.get("id")}
        for name in ("detail", "overview", "routes"):
            self.assertIn(f"itinerary-view-{name}", ids)
            self.assertTrue(any(tag == "label" and attrs.get("for") == f"itinerary-view-{name}" for tag, attrs in document.elements))
        self.assertTrue(any(tag == "details" and "open" in attrs for tag, attrs in document.elements))
        self.assertIn("#itinerary-view-overview:checked", " ".join(document.text))

    def test_export_does_not_mutate_source_data(self) -> None:
        data = media_fixture()
        before = copy.deepcopy(data)
        renderer.build(data, private_offline=True)
        self.assertEqual(data, before)
        renderer.build(data)
        self.assertEqual(data, before)

    def test_cli_selects_profile_without_rewriting_input(self) -> None:
        data = media_fixture()
        source = json.dumps(data, ensure_ascii=False).encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "itinerary.json"
            input_path.write_bytes(source)
            for private_offline in (False, True):
                output_path = root / ("offline.html" if private_offline else "default.html")
                command = [str(MODULE_PATH), str(input_path), str(output_path)]
                if private_offline:
                    command.append("--private-offline")
                with patch.object(sys, "argv", command), redirect_stdout(io.StringIO()):
                    renderer.main()
                self.assertEqual(output_path.read_text(encoding="utf-8"), renderer.build(data, private_offline=private_offline))
                self.assertEqual(input_path.read_bytes(), source)


if __name__ == "__main__":
    unittest.main()
