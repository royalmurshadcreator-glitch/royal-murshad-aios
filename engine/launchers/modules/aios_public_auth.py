"""Session authentication and strict same-origin checks for local API requests."""

from urllib.parse import urlsplit

from fastapi.responses import JSONResponse


_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}


def _same_loopback_origin(request):
    origin = request.headers.get("origin")
    if not origin or request.url.hostname not in _LOOPBACK_HOSTS:
        return False
    try:
        parsed = urlsplit(origin)
        return (
            parsed.scheme == request.url.scheme
            and parsed.netloc.lower() == request.url.netloc.lower()
            and parsed.hostname in _LOOPBACK_HOSTS
            and parsed.path in ("", "/")
            and not parsed.query
            and not parsed.fragment
        )
    except (TypeError, ValueError):
        return False


async def basic_auth_middleware(request, call_next):
    """Resolve a server-side session; authorization is enforced by RBAC below."""
    request.state.auth_identity = None
    if request.url.path.startswith("/api/") and request.method in _STATE_CHANGING:
        if not _same_loopback_origin(request):
            return JSONResponse(status_code=403, content={"detail": "same_origin_required"})

    token = request.cookies.get("royal_session")
    if token:
        try:
            import auth

            result = auth.whoami(token)
            if result.get("ok"):
                request.state.auth_identity = result.get("user")
        except Exception:
            # Fail closed without logging credentials, tokens, or exception text.
            request.state.auth_identity = None
    return await call_next(request)
