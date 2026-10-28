"""Route-level tests for the cookie session API against a temporary auth DB."""

import asyncio
import importlib.util
import json
import secrets
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException, Response
from starlette.requests import Request


PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUTH_SOURCE = PROJECT_ROOT / "Royal Murshad AIOS - API" / "Royal Murshad AIOS - aios_auth" / "Royal Murshad AIOS - aios_auth.py"
API_SOURCE = PROJECT_ROOT / "Royal Murshad AIOS - API" / "Royal Murshad AIOS - aios_auth" / "Royal Murshad AIOS - aios_user_auth_api.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_request(body=None, origin="http://127.0.0.1:9000", cookie=None):
    body_bytes = json.dumps(body or {}).encode("utf-8")
    headers = [
        (b"host", b"127.0.0.1:9000"),
        (b"origin", origin.encode("ascii")),
        (b"content-type", b"application/json"),
    ]
    if cookie:
        headers.append((b"cookie", ("royal_session=" + cookie).encode("ascii")))

    async def receive():
        return {"type": "http.request", "body": body_bytes, "more_body": False}

    return Request({
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1", "method": "POST", "scheme": "http",
        "path": "/api/auth/login", "raw_path": b"/api/auth/login", "query_string": b"",
        "root_path": "", "headers": headers,
        "server": ("127.0.0.1", 9000), "client": ("127.0.0.1", 30000),
    }, receive)


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.auth = load_module("royal_auth_api_test_store", AUTH_SOURCE)
        self.auth.MEM_DB = Path(self.temp.name) / "auth.sqlite3"
        self.password = secrets.token_urlsafe(24)
        self.auth.provision_first_admin("local-admin", self.password)
        self.previous_auth = sys.modules.get("auth")
        sys.modules["auth"] = self.auth
        self.api = load_module("royal_user_auth_api_test", API_SOURCE)

    def tearDown(self):
        if self.previous_auth is None:
            sys.modules.pop("auth", None)
        else:
            sys.modules["auth"] = self.previous_auth
        self.temp.cleanup()

    def test_login_issues_http_only_strict_same_origin_cookie(self):
        response = Response()
        result = asyncio.run(self.api.login(
            make_request({"username": "local-admin", "password": self.password}), response
        ))
        self.assertTrue(result["ok"])
        cookie = response.headers.get("set-cookie", "").lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=strict", cookie)
        self.assertIn("max-age=28800", cookie)
        token = response.headers.get("set-cookie", "").split(";", 1)[0].split("=", 1)[1]
        self.assertTrue(self.auth.whoami(token)["ok"])

    def test_cross_origin_login_is_rejected(self):
        with self.assertRaises(HTTPException) as rejected:
            asyncio.run(self.api.login(
                make_request({"username": "local-admin", "password": self.password}, "http://evil.example"),
                Response(),
            ))
        self.assertEqual(rejected.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
