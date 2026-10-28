"""Restrict browser CORS to the same loopback origins as the local UI."""

from fastapi.responses import Response


ALLOWED_ORIGINS = {"http://127.0.0.1:9000", "http://localhost:9000"}
ALLOWED_METHODS = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
ALLOWED_HEADERS = "Accept, Content-Type, Authorization, X-CSRF-Token"


async def cors_middleware(request, call_next):
    origin = request.headers.get("origin")
    if request.method == "OPTIONS":
        if origin not in ALLOWED_ORIGINS:
            return Response(status_code=403)
        requested_method = request.headers.get("access-control-request-method", "").upper()
        if requested_method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            return Response(status_code=403)
        return Response(status_code=204, headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": ALLOWED_METHODS,
            "Access-Control-Allow-Headers": ALLOWED_HEADERS,
            "Vary": "Origin",
        })

    response = await call_next(request)
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    else:
        for header in ("access-control-allow-origin", "access-control-allow-credentials"):
            if header in response.headers:
                del response.headers[header]
    return response
