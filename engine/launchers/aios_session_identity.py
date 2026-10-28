"""Session identity middleware + dependencies for Royal Murshad AIOS."""
from __future__ import annotations
import sqlite3, sys
from datetime import datetime, timezone
from fastapi import Request, HTTPException

LEADS = r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_leads"
if LEADS not in sys.path:
    sys.path.insert(0, LEADS)

import jwt
import aios_auth_core

DB      = aios_auth_core.DB
_secret = aios_auth_core._secret


def resolve_identity(token):
    if not token:
        return None
    try:
        claims = jwt.decode(token, _secret(), algorithms=["HS256"])
    except Exception:
        return None
    try:
        uid = int(claims.get("sub"))
    except (TypeError, ValueError):
        return None
    conn = sqlite3.connect(str(DB)); conn.row_factory = sqlite3.Row
    try:
        now = datetime.now(timezone.utc).isoformat()
        row = conn.execute(
            "SELECT user_id FROM aios_sessions WHERE token=? AND expires_at > ?",
            (token, now)).fetchone()
        if not row:
            return None
        user = conn.execute(
            "SELECT id, username, role FROM aios_users WHERE id=?", (uid,)).fetchone()
        if not user:
            return None
        return {"user_id": user["id"], "username": user["username"], "role": user["role"]}
    finally:
        conn.close()


async def session_identity_middleware(request, call_next):
    request.state.user_id  = None
    request.state.role     = None
    request.state.username = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        ident = resolve_identity(auth[7:].strip())
        if ident:
            request.state.user_id  = ident["user_id"]
            request.state.role     = ident["role"]
            request.state.username = ident["username"]
    return await call_next(request)


def get_current_user(request):
    uid = getattr(request.state, "user_id", None)
    if uid is None:
        raise HTTPException(401, "authentication required")
    return {"user_id": uid,
            "username": getattr(request.state, "username", None),
            "role":     getattr(request.state, "role", None)}


def require_admin(request):
    u = get_current_user(request)
    if u["role"] not in ("admin", "owner"):
        raise HTTPException(403, "administrator privileges required")
    return u
