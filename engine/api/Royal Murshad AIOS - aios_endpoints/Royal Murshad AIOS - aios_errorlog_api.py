"""Royal Jarvis — Error Log API."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import aios_errorlog as el

router = APIRouter(prefix="/api/errorlog", tags=["errorlog"])


class LogIn(BaseModel):
    module: str
    level: str = "error"
    message: str
    meta: dict | None = None


@router.post("/log")
def log_error(req: LogIn):
    try:
        return el.log(req.module, req.level, req.message, req.meta)
    except Exception as e:
        raise HTTPException(500, str(e)[:200])


@router.get("/recent")
def recent(limit: int = 50, module: str | None = None, level: str | None = None):
    try:
        return {"ok": True, "items": el.recent(limit, module, level)}
    except Exception as e:
        raise HTTPException(500, str(e)[:200])


@router.get("/stats")
def stats():
    try:
        return el.stats()
    except Exception as e:
        raise HTTPException(500, str(e)[:200])


@router.post("/purge")
def purge(days: int = 30):
    try:
        return el.purge_old(days)
    except Exception as e:
        raise HTTPException(500, str(e)[:200])
