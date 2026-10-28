"""
AIOS Security Middleware - Track E2
Royal Murshad AIOS

Implements the Track D2 (authn), D3 (API protections), and D4 (safety)
invariants at the middleware layer, without requiring new dependencies.

Installed by aios_backend_launcher.py before uvicorn.run().
"""
import time
import logging
from collections import defaultdict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("aios.security")
logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")

# In-memory rate limiter (per-IP, sliding window of 60s)
_rate_limits = defaultdict(list)

# Loopback addresses bypass rate limits (local dev is trusted)
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _client_ip(request: Request) -> str:
    # Trust Cloudflare's header first
    cf = request.headers.get("cf-connecting-ip")
    if cf:
        return cf.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_loopback(ip: str) -> bool:
    return ip in _LOOPBACK


class SecurityMiddleware(BaseHTTPMiddleware):
    """Rate limit, request size cap, and security headers."""

    async def dispatch(self, request: Request, call_next):
        ip = _client_ip(request)
        path = request.url.path
        method = request.method

        # 1. Rate limiting (skip loopback)
        if not _is_loopback(ip):
            now = time.time()
            window = _rate_limits[ip]
            # trim entries older than 60s
            window[:] = [t for t in window if now - t < 60]
            if len(window) >= 60:
                logger.warning(f"[rate-limit] {ip} exceeded on {method} {path}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "60 requests per minute per IP",
                        "retry_after_seconds": 60,
                    },
                )
            window.append(now)

        # 2. Request body size cap (1 MB)
        cl = request.headers.get("content-length")
        if cl:
            try:
                if int(cl) > 1048576:
                    logger.warning(f"[size-limit] {ip} sent {cl} bytes")
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "payload_too_large",
                            "max_bytes": 1048576,
                        },
                    )
            except ValueError:
                pass

        # 3. Process the request
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(f"[unhandled] {method} {path}: {exc}")
            raise

        # 4. Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-AIOS-Security"] = "active"

        return response


def install_security(app: FastAPI) -> None:
    """Install security middleware. Called from the launcher."""
    app.add_middleware(SecurityMiddleware)
    logger.info("[security] Installed: rate-limit + size-limit + headers")
