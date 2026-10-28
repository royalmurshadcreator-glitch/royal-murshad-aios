"""
ROYAL JARVIS - Auth HTTP API (Phase 40)
Endpoints under /api/auth/*. Uses the product-local auth module bound by the launcher.
"""
from fastapi import APIRouter, HTTPException, Request, Response, Cookie
from typing import Optional
import os

router = APIRouter(prefix="/api/auth", tags=["auth"])

def _require_same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    host = request.url.netloc
    if not origin or not host or request.url.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise HTTPException(403, "same_origin_required")
    from urllib.parse import urlsplit
    try:
        parsed = urlsplit(origin)
        if (
            parsed.scheme != request.url.scheme
            or parsed.netloc.lower() != host.lower()
            or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise HTTPException(403, "origin_not_allowed")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(403, "origin_not_allowed")

COOKIE = "royal_session"
MAX_AGE = 8 * 60 * 60
COOKIE_SECURE = os.environ.get("ROYAL_AUTH_COOKIE_SECURE", "0").strip() == "1"


def _a():
    import auth
    return auth


@router.post("/login")
async def login(request: Request, response: Response):
    _require_same_origin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "invalid json")
    if not isinstance(body, dict):
        raise HTTPException(400, "invalid json")
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        raise HTTPException(400, "username and password required")
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    r = _a().login(username, password, ip=ip, user_agent=ua)
    if not r.get("ok"):
        raise HTTPException(401, r.get("error", "login_failed"))
    response.set_cookie(
        key=COOKIE,
        value=r["token"],
        max_age=MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"ok": True, "user": r["user"], "expires_at": r["expires_at"]}


@router.post("/logout")
async def logout(request: Request, response: Response, royal_session: Optional[str] = Cookie(default=None)):
    _require_same_origin(request)
    if royal_session:
        try:
            _a().logout(royal_session)
        except Exception:
            pass
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
async def me(royal_session: Optional[str] = Cookie(default=None)):
    r = _a().whoami(royal_session or "")
    if not r.get("ok"):
        raise HTTPException(401, r.get("error", "not_authenticated"))
    return {"ok": True, "user": r["user"], "expires_at": r["expires_at"]}


@router.get("/users")
async def list_users(royal_session: Optional[str] = Cookie(default=None)):
    r = _a().whoami(royal_session or "")
    if not r.get("ok"):
        raise HTTPException(401, "not_authenticated")
    if r["user"]["role"] != "admin":
        raise HTTPException(403, "admin_required")
    return {"ok": True, "users": _a().list_users()}


@router.post("/users/create")
async def create_user(request: Request, royal_session: Optional[str] = Cookie(default=None)):
    r = _a().whoami(royal_session or "")
    if not r.get("ok"):
        raise HTTPException(401, "not_authenticated")
    if r["user"]["role"] != "admin":
        raise HTTPException(403, "admin_required")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "invalid json")
    res = _a().create_user(
        (body.get("username") or "").strip(),
        body.get("password") or "",
        display_name=body.get("display_name"),
        email=body.get("email"),
        role=body.get("role") or "user",
    )
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "create_failed"))
    return res


@router.delete("/users/{username}")
async def delete_user(username: str, royal_session: Optional[str] = Cookie(default=None)):
    r = _a().whoami(royal_session or "")
    if not r.get("ok"):
        raise HTTPException(401, "not_authenticated")
    if r["user"]["role"] != "admin":
        raise HTTPException(403, "admin_required")
    res = _a().delete_user(username)
    if not res.get("ok"):
        raise HTTPException(400, res.get("error", "delete_failed"))
    return res



@router.post("/password")
async def change_password(request: Request, royal_session: Optional[str] = Cookie(default=None)):
    _require_same_origin(request)
    identity = _a().whoami(royal_session or "")
    if not identity.get("ok"):
        raise HTTPException(401, "not_authenticated")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "invalid_json")

    result = _a().change_password_with_current(
        identity["user"]["username"],
        body.get("current_password") or "",
        body.get("new_password") or "",
    )
    if not result.get("ok"):
        code = result.get("error", "change_failed")
        if code == "invalid_current_password":
            raise HTTPException(401, "invalid_current_password")
        raise HTTPException(400, code)
    return result


@router.get("/profile")
async def get_profile(royal_session: Optional[str] = Cookie(default=None)):
    identity = _a().whoami(royal_session or "")
    if not identity.get("ok"):
        raise HTTPException(401, "not_authenticated")
    return {"ok": True, "user": identity["user"]}


@router.put("/profile")
async def put_profile(request: Request, royal_session: Optional[str] = Cookie(default=None)):
    _require_same_origin(request)
    identity = _a().whoami(royal_session or "")
    if not identity.get("ok"):
        raise HTTPException(401, "not_authenticated")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "invalid_json")

    current = identity["user"]
    display_name = body.get("display_name", current.get("display_name"))
    email = body.get("email", current.get("email"))
    result = _a().update_profile(
        current["username"], display_name=display_name, email=email
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "profile_update_failed"))
    return result


@router.post("/recovery/reset")
async def reset_password_from_recovery(request: Request):
    # Codes are generated by a local utility, never by a public issue endpoint.
    _require_same_origin(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "invalid_json")

    username = body.get("username")
    code = body.get("recovery_code")
    password = body.get("new_password")
    if not all(isinstance(x, str) and x for x in (username, code, password)):
        raise HTTPException(400, "recovery_fields_required")
    if len(password) < 16:
        raise HTTPException(400, "password_too_short")

    result = _a().reset_password_with_recovery(username.strip(), code, password)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "recovery_failed"))
    return {
        "ok": True,
        "password_reset": True,
        "sessions_invalidated": True,
    }
