"""Isolated auth/RBAC tests using fake server-side session resolution."""

import asyncio
import importlib.util
import secrets
import sys
import unittest
from pathlib import Path
from types import ModuleType

from starlette.requests import Request
from starlette.responses import Response


MODULE_DIR = Path(__file__).resolve().parent


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, MODULE_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


public_auth = _load("auth_middleware_under_test", "aios_public_auth.py")
session_identity = _load("identity_middleware_under_test", "aios_session_identity.py")
rbac = _load("rbac_middleware_under_test", "aios_rbac_middleware.py")


def _request(path="/api/chat/send", method="GET", headers=()):
    return Request({
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1", "method": method, "scheme": "http",
        "path": path, "raw_path": path.encode(), "query_string": b"",
        "root_path": "", "headers": list(headers),
        "server": ("127.0.0.1", 9000), "client": ("127.0.0.1", 30000),
    })


def _pipeline(request):
    async def endpoint(_request):
        return Response("allowed", status_code=200)

    async def after_auth(req):
        async def after_identity(identity_req):
            return await rbac.rbac_middleware(identity_req, endpoint)
        return await session_identity.session_identity_middleware(req, after_identity)

    return asyncio.run(public_auth.basic_auth_middleware(request, after_auth))


class AuthMiddlewareTests(unittest.TestCase):
    def setUp(self):
        self.old_auth = sys.modules.get("auth")
        fake = ModuleType("auth")
        fake.whoami = lambda token: {"ok": False, "error": "invalid_token"}
        sys.modules["auth"] = fake

    def tearDown(self):
        if self.old_auth is None:
            sys.modules.pop("auth", None)
        else:
            sys.modules["auth"] = self.old_auth

    def test_unauthenticated_and_invalid_session_are_denied(self):
        self.assertEqual(_pipeline(_request()).status_code, 401)
        token = secrets.token_urlsafe(32)
        request = _request(headers=[(b"cookie", ("royal_session=" + token).encode())])
        self.assertEqual(_pipeline(request).status_code, 401)

    def test_authenticated_admin_can_access_api_but_user_role_cannot(self):
        import auth
        auth.whoami = lambda _token: {"ok": True, "user": {"id": 1, "username": "test-admin", "role": "admin"}}
        token = secrets.token_urlsafe(32)
        request = _request(headers=[(b"cookie", ("royal_session=" + token).encode())])
        self.assertEqual(_pipeline(request).status_code, 200)
        auth.whoami = lambda _token: {"ok": True, "user": {"id": 2, "username": "test-user", "role": "user"}}
        request = _request(headers=[(b"cookie", ("royal_session=" + token).encode())])
        self.assertEqual(_pipeline(request).status_code, 403)

    def test_forged_cross_origin_write_is_rejected(self):
        import auth
        auth.whoami = lambda _token: {"ok": True, "user": {"id": 1, "username": "test-admin", "role": "admin"}}
        token = secrets.token_urlsafe(32)
        request = _request(
            method="POST",
            headers=[
                (b"cookie", ("royal_session=" + token).encode()),
                (b"origin", b"http://attacker.example"),
            ],
        )
        self.assertEqual(_pipeline(request).status_code, 403)

    def test_same_origin_write_is_allowed_for_admin(self):
        import auth
        auth.whoami = lambda _token: {"ok": True, "user": {"id": 1, "username": "test-admin", "role": "admin"}}
        token = secrets.token_urlsafe(32)
        request = _request(
            method="POST",
            headers=[
                (b"cookie", ("royal_session=" + token).encode()),
                (b"origin", b"http://127.0.0.1:9000"),
            ],
        )
        self.assertEqual(_pipeline(request).status_code, 200)

    def test_public_assets_remain_available_without_auth(self):
        response = _pipeline(_request(path="/static-workspace/index.html"))
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
