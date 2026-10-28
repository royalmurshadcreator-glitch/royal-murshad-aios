"""Safe tests for deployed app path handling and public asset filtering."""

import ast
import asyncio
import copy
import pathlib
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

MODULES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULES_DIR.parents[2]
LAUNCHER_PATH = PROJECT_ROOT / "18_ENV" / "launchers" / "aios_backend_launcher.py"
sys.path.insert(0, str(MODULES_DIR))
from aios_dashboard_security import (
    APP_DEPLOY_ALLOWED_SUFFIXES,
    ApprovedStaticFiles,
    build_app_deploy_allowlist,
    resolve_app_deployment_html,
)


async def _request_asgi(app, path):
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": path, "raw_path": path.encode("ascii"), "query_string": b"",
        "root_path": "/apps-deploy", "headers": [],
        "server": ("test", 80), "client": ("test", 1),
    }
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    try:
        await app(scope, receive, send)
    except StarletteHTTPException as exc:
        return exc.status_code, b""
    status = next(message["status"] for message in sent if message["type"] == "http.response.start")
    body = b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")
    return status, body


def _load_route_function(namespace):
    tree = ast.parse(LAUNCHER_PATH.read_text(encoding="utf-8"))
    route = next(node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef) and node.name == "load_app")
    route = copy.deepcopy(route)
    route.decorator_list = []
    module = ast.Module(body=[route], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(LAUNCHER_PATH), "exec"), namespace)
    return namespace["load_app"]


class AppDeploymentSecurityTests(unittest.TestCase):
    def test_allowlist_keeps_public_assets_and_excludes_runtime_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            public = root / "Royal Murshad AIOS - royal-finance"
            public.mkdir()
            (public / "index.html").write_text("public app", encoding="utf-8")
            (public / "app.js").write_text("public script", encoding="utf-8")
            (root / "server_errors.log").write_text("private", encoding="utf-8")
            (root / "servers.json").write_text("{}", encoding="utf-8")
            (root / "run_servers.py").write_text("private", encoding="utf-8")
            (root / "index.html.bak").write_text("private", encoding="utf-8")
            backup = root / "_branding_backup" / "Royal Murshad AIOS - royal-old"
            backup.mkdir(parents=True)
            (backup / "index.html").write_text("private backup", encoding="utf-8")

            allowed = build_app_deploy_allowlist(root)
            self.assertIn("Royal Murshad AIOS - royal-finance/index.html", allowed)
            self.assertIn("Royal Murshad AIOS - royal-finance/app.js", allowed)
            self.assertFalse(any(path.endswith((".log", ".json", ".py", ".bak")) for path in allowed))
            self.assertFalse(any("backup" in path.casefold() for path in allowed))
            self.assertEqual(APP_DEPLOY_ALLOWED_SUFFIXES, frozenset({".html", ".js", ".css", ".jpg", ".jpeg", ".png", ".svg", ".webp", ".ico"}))

            files = ApprovedStaticFiles(directory=root, allowed_paths=allowed, html=True)
            status, body = asyncio.run(_request_asgi(files, "/Royal Murshad AIOS - royal-finance/index.html"))
            self.assertEqual((status, body), (200, b"public app"))
            for path in ("/server_errors.log", "/servers.json", "/run_servers.py", "/index.html.bak"):
                with self.subTest(path=path):
                    status, _ = asyncio.run(_request_asgi(files, path))
                    self.assertEqual(status, 404)

    def test_deployment_path_resolution_rejects_bad_slugs_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "apps"
            app_dir = root / "Royal Murshad AIOS - royal-finance"
            app_dir.mkdir(parents=True)
            page = app_dir / "index.html"
            page.write_text("safe", encoding="utf-8")
            self.assertEqual(resolve_app_deployment_html(root, "finance"), page.resolve())
            for slug in ("../outside", "..\\outside", "finance/../../outside", "bad.slug"):
                with self.subTest(slug=slug):
                    with self.assertRaises(ValueError):
                        resolve_app_deployment_html(root, slug)

            outside = Path(temp_dir) / "outside.html"
            outside.write_text("outside", encoding="utf-8")
            linked = root / "Royal Murshad AIOS - royal-linked"
            linked.mkdir()
            try:
                (linked / "index.html").symlink_to(outside)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            with self.assertRaises(ValueError):
                resolve_app_deployment_html(root, "linked")

    def test_real_load_app_route_uses_only_temporary_deployment_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app_dir = root / "Royal Murshad AIOS - royal-finance"
            app_dir.mkdir()
            (app_dir / "index.html").write_text("<html><head></head>finance</html>", encoding="utf-8")
            route = _load_route_function(
                {
                    "apps_dir": root,
                    "HTMLResponse": HTMLResponse,
                    "resolve_app_deployment_html": resolve_app_deployment_html,
                    "_pathlib": pathlib,
                }
            )

            response = asyncio.run(route("finance"))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"finance", response.body)
            self.assertIn(b"/apps-deploy/Royal%20Murshad%20AIOS%20-%20royal-finance/", response.body)
            with self.assertRaises(HTTPException) as rejected:
                asyncio.run(route("../outside"))
            self.assertEqual(rejected.exception.status_code, 400)
            self.assertEqual(asyncio.run(route("missing")).status_code, 404)


if __name__ == "__main__":
    unittest.main()
