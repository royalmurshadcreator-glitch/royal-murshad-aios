"""Unit tests for the loopback-only browser CORS policy."""

import asyncio
import importlib.util
import unittest
from pathlib import Path

from starlette.requests import Request
from starlette.responses import Response


MODULE_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cors_policy_test", MODULE_DIR / "aios_cors.py")
cors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cors)


def request(method, headers):
    return Request({
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1", "method": method, "scheme": "http",
        "path": "/api/chat/send", "raw_path": b"/api/chat/send", "query_string": b"",
        "root_path": "", "headers": headers,
        "server": ("127.0.0.1", 9000), "client": ("127.0.0.1", 30000),
    })


class CorsPolicyTests(unittest.TestCase):
    def test_allowed_loopback_preflight_is_narrow(self):
        req = request("OPTIONS", [
            (b"origin", b"http://127.0.0.1:9000"),
            (b"access-control-request-method", b"POST"),
        ])
        response = asyncio.run(cors.cors_middleware(req, lambda _req: None))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://127.0.0.1:9000")
        self.assertEqual(response.headers["access-control-allow-credentials"], "true")
        self.assertNotIn("*", response.headers["access-control-allow-headers"])

    def test_unapproved_origin_and_method_are_rejected(self):
        evil = request("OPTIONS", [
            (b"origin", b"http://attacker.example"),
            (b"access-control-request-method", b"POST"),
        ])
        self.assertEqual(asyncio.run(cors.cors_middleware(evil, lambda _req: None)).status_code, 403)
        method = request("OPTIONS", [
            (b"origin", b"http://127.0.0.1:9000"),
            (b"access-control-request-method", b"TRACE"),
        ])
        self.assertEqual(asyncio.run(cors.cors_middleware(method, lambda _req: None)).status_code, 403)

    def test_unapproved_origin_does_not_retain_inner_wildcard_headers(self):
        req = request("GET", [(b"origin", b"http://attacker.example")])

        async def inner(_req):
            return Response(headers={"Access-Control-Allow-Origin": "*"})

        response = asyncio.run(cors.cors_middleware(req, inner))
        self.assertNotIn("access-control-allow-origin", response.headers)


if __name__ == "__main__":
    unittest.main()
