"""
ASG Store — Auth API
FastAPI router with register, login, logout, me endpoints.

Mount in aios_server.py:
    from aios_endpoints.aios_store_auth_api import router as store_auth_router
    app.include_router(store_auth_router)
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import sys
from pathlib import Path

# Ensure memory module is importable
sys.path.insert(0, str(Path(r"D:\01_PROJECTS\AIOS\04_MEMORY\aios_memory")))

try:
    import aios_store_users as users
except ImportError:
    users = None

router = APIRouter(prefix="/api/store/auth", tags=["store-auth"])


class RegisterReq(BaseModel):
    email: str
    password: str
    name: str
    company: Optional[str] = ""


class LoginReq(BaseModel):
    email: str
    password: str


class TokenReq(BaseModel):
    token: str


@router.get("/status")
def status():
    return {"ok": True, "available": users is not None, "db": "store_users.db"}


@router.post("/register")
def register(req: RegisterReq):
    if users is None:
        raise HTTPException(500, "user store not available")
    r = users.register(req.email, req.password, req.name, req.company or "")
    if not r.get("ok"):
        raise HTTPException(400, r.get("error", "register_failed"))
    # Auto-login after register
    lr = users.login(req.email, req.password)
    return {"ok": True, "user": lr["user"], "token": lr["token"]}


@router.post("/login")
def login(req: LoginReq):
    if users is None:
        raise HTTPException(500, "user store not available")
    r = users.login(req.email, req.password)
    if not r.get("ok"):
        raise HTTPException(401, r.get("error", "login_failed"))
    return r


@router.post("/logout")
def logout(req: TokenReq):
    if users is None:
        raise HTTPException(500, "user store not available")
    return users.logout(req.token)


@router.get("/me")
def me(authorization: Optional[str] = Header(None)):
    if users is None:
        raise HTTPException(500, "user store not available")
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    user = users.verify_token(token)
    if not user:
        raise HTTPException(401, "invalid_token")
    return {"ok": True, "user": user}


@router.post("/cleanup")
def cleanup():
    if users is None:
        raise HTTPException(500, "user store not available")
    return {"ok": True, "deleted": users.cleanup_expired_sessions()}
