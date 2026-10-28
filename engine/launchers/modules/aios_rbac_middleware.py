"""Fail-closed local-beta authorization policy for the HTTP API."""

from fastapi.responses import JSONResponse


_PUBLIC_API_PATHS = {
    "/api/auth/login",
    "/api/auth/recovery/reset",
}


async def rbac_middleware(request, call_next):
    path = request.url.path
    is_api = path == "/api" or path.startswith("/api/")
    if not is_api or path in _PUBLIC_API_PATHS:
        return await call_next(request)

    identity = getattr(request.state, "user", None)
    if not identity:
        return JSONResponse(status_code=401, content={"detail": "authentication_required"})
    if identity.get("role") not in {"admin", "owner"}:
        return JSONResponse(status_code=403, content={"detail": "administrator_required"})
    return await call_next(request)
