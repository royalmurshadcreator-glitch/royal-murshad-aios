"""Filesystem boundary tests; fixtures are temporary and contain no user data."""

import sys
import asyncio
import tempfile
import unittest
from pathlib import Path

from starlette.exceptions import HTTPException as StarletteHTTPException

sys.path.insert(0, str(Path(__file__).parent))
from aios_dashboard_security import (
    ApprovedStaticFiles,
    DASHBOARD_ASSET_ALLOWED_FILES,
    DASHBOARD_PUBLIC_ALLOWED_FILES,
    PUBLIC_UI_ALLOWED_FILES,
    resolve_dashboard_html,
)


async def _request_asgi(app, path):
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "/static-workspace",
        "headers": [],
        "server": ("test", 80),
        "client": ("test", 1),
    }
    sent = []
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    try:
        await app(scope, receive, send)
    except StarletteHTTPException as exc:
        return exc.status_code, b"", ["http.exception"]
    status = next(message["status"] for message in sent if message["type"] == "http.response.start")
    body = b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")
    return status, body, [message["type"] for message in sent]


class ApprovedStaticFilesTests(unittest.TestCase):
    def test_valid_public_asset_is_available(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("public", encoding="utf-8")
            files = ApprovedStaticFiles(directory=root, allowed_paths=PUBLIC_UI_ALLOWED_FILES)
            path, stat = files.lookup_path("index.html")
            self.assertEqual(Path(path).read_text(encoding="utf-8"), "public")
            self.assertIsNotNone(stat)

    def test_missing_public_asset_is_not_found(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            files = ApprovedStaticFiles(directory=temp_dir, allowed_paths=PUBLIC_UI_ALLOWED_FILES)
            path, stat = files.lookup_path("styles.css")
            self.assertEqual(path, "")
            self.assertIsNone(stat)

    def test_private_and_traversal_paths_are_not_allowlisted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("private", encoding="utf-8")
            files = ApprovedStaticFiles(directory=root, allowed_paths=PUBLIC_UI_ALLOWED_FILES)
            for name in ("README.md", "../../.git/config", "18_ENV/launchers/aios_backend_launcher.py"):
                with self.subTest(name=name):
                    path, stat = files.lookup_path(name)
                    self.assertEqual(path, "")
                    self.assertIsNone(stat)

    def test_asgi_serves_public_asset_and_rejects_private_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("public", encoding="utf-8")
            (root / "README.md").write_text("private", encoding="utf-8")
            files = ApprovedStaticFiles(directory=root, allowed_paths=PUBLIC_UI_ALLOWED_FILES)
            status, body, messages = asyncio.run(_request_asgi(files, "/index.html"))
            self.assertEqual(status, 200)
            self.assertEqual(body, b"public", messages)
            for path in ("/README.md", "/../../outside.txt"):
                with self.subTest(path=path):
                    status, _, _ = asyncio.run(_request_asgi(files, path))
                    self.assertEqual(status, 404)

    def test_dashboard_files_and_referenced_assets_have_separate_allowlists(self):
        self.assertIn("index.html", DASHBOARD_PUBLIC_ALLOWED_FILES)
        self.assertIn("aios-design-system.css", DASHBOARD_PUBLIC_ALLOWED_FILES)
        self.assertNotIn("manifest.json", DASHBOARD_PUBLIC_ALLOWED_FILES)
        self.assertIn("favicon.ico", DASHBOARD_ASSET_ALLOWED_FILES)
        self.assertNotIn("README.md", DASHBOARD_ASSET_ALLOWED_FILES)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("dashboard", encoding="utf-8")
            (root / "README.md").write_text("private", encoding="utf-8")
            pages = ApprovedStaticFiles(directory=root, allowed_paths=DASHBOARD_PUBLIC_ALLOWED_FILES)
            status, body, _ = asyncio.run(_request_asgi(pages, "/index.html"))
            self.assertEqual((status, body), (200, b"dashboard"))
            status, _, _ = asyncio.run(_request_asgi(pages, "/README.md"))
            self.assertEqual(status, 404)


class DashboardContainmentTests(unittest.TestCase):
    def test_root_and_valid_dashboard_page_resolve(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "index.html").write_text("home", encoding="utf-8")
            (root / "about.html").write_text("about", encoding="utf-8")
            self.assertEqual(resolve_dashboard_html(root).name, "index.html")
            self.assertEqual(resolve_dashboard_html(root, "about.html").name, "about.html")

    def test_relative_traversal_and_absolute_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "public"
            root.mkdir()
            outside = Path(temp_dir) / "outside.html"
            outside.write_text("outside", encoding="utf-8")
            for requested in ("../outside.html", str(outside)):
                with self.subTest(requested=requested):
                    with self.assertRaises(ValueError):
                        resolve_dashboard_html(root, requested)

    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "public"
            root.mkdir()
            outside = Path(temp_dir) / "outside.html"
            outside.write_text("outside", encoding="utf-8")
            link = root / "linked.html"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            with self.assertRaises(ValueError):
                resolve_dashboard_html(root, "linked.html")

    def test_non_html_and_missing_dashboard_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "notes.txt").write_text("not a dashboard", encoding="utf-8")
            for requested in ("notes.txt", "missing.html"):
                with self.subTest(requested=requested):
                    with self.assertRaises(FileNotFoundError):
                        resolve_dashboard_html(root, requested)


if __name__ == "__main__":
    unittest.main()
