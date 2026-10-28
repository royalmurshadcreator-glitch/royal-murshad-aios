"""Exercise the actual FastAPI middleware order without starting a service."""

import asyncio
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import ModuleType

from fastapi import FastAPI
from fastapi.responses import JSONResponse


MODULE_DIR = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, MODULE_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


public_auth = load("public_auth_asgi_test", "aios_public_auth.py")
session_identity = load("session_identity_asgi_test", "aios_session_identity.py")
rbac = load("rbac_asgi_test", "aios_rbac_middleware.py")

app = FastAPI()
app.middleware("http")(rbac.rbac_middleware)
app.middleware("http")(session_identity.session_identity_middleware)
app.middleware("http")(public_auth.basic_auth_middleware)


@app.get("/api/private")
async def private_route():
    return {"ok": True}


@app.get("/static-workspace/index.html")
async def public_asset():
    return JSONResponse({"asset": "public"})


async def request(path, cookie=None, method="GET", origin=None):
    headers = []
    if cookie:
        headers.append((b"cookie", ("royal_session=" + cookie).encode()))
    if origin:
        headers.append((b"origin", origin.encode()))
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1", "method": method, "scheme": "http",
        "path": path, "raw_path": path.encode(), "query_string": b"",
        "root_path": "", "headers": headers,
        "server": ("127.0.0.1", 9000), "client": ("127.0.0.1", 30000),
    }
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

    async def send(message):
        sent.append(message)

    await app(scope, receive, send)
    start = next(x for x in sent if x["type"] == "http.response.start")
    body = b"".join(x.get("body", b"") for x in sent if x["type"] == "http.response.body")
    return start["status"], json.loads(body) if body else None


class AuthMiddlewareOrderTests(unittest.TestCase):
    def setUp(self):
        self.old_auth = sys.modules.get("auth")
        auth = ModuleType("auth")
        auth.whoami = lambda _token: {"ok": False}
        sys.modules["auth"] = auth

    def tearDown(self):
        if self.old_auth is None:
            sys.modules.pop("auth", None)
        else:
            sys.modules["auth"] = self.old_auth

    def test_real_app_middleware_order_denies_missing_session_and_allows_admin(self):
        denied, _ = asyncio.run(request("/api/private"))
        self.assertEqual(denied, 401)
        sys.modules["auth"].whoami = lambda _token: {
            "ok": True, "user": {"id": 1, "username": "local-admin", "role": "admin"}
        }
        allowed, _ = asyncio.run(request("/api/private", cookie="temporary-test-session"))
        self.assertEqual(allowed, 200)

    def test_real_app_middleware_order_keeps_public_assets_unauthenticated(self):
        status, body = asyncio.run(request("/static-workspace/index.html"))
        self.assertEqual(status, 200)
        self.assertEqual(body, {"asset": "public"})


if __name__ == "__main__":
    unittest.main()
