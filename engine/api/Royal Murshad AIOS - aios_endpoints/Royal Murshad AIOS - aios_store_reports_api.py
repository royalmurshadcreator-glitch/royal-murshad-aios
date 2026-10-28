"""
ASG Store — Reports API
Endpoints:
    POST /api/store/reports/submit
    GET  /api/store/reports/open
    GET  /api/store/reports/for-app/{app_id}
    POST /api/store/reports/resolve
    GET  /api/store/reports/stats
"""
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

sys.path.insert(0, str(Path(r"D:\01_PROJECTS\AIOS\04_MEMORY\aios_memory")))

try:
    import aios_store_reports as reports
except ImportError:
    reports = None

router = APIRouter(prefix="/api/store/reports", tags=["store-reports"])


class SubmitReq(BaseModel):
    app_id: str
    reason: str
    details: Optional[str] = ""
    reporter_email: Optional[str] = ""


class ResolveReq(BaseModel):
    id: str
    notes: Optional[str] = ""


@router.get("/stats")
def stats():
    if reports is None:
        raise HTTPException(500, "module_unavailable")
    return reports.stats()


@router.post("/submit")
def submit(req: SubmitReq):
    if reports is None:
        raise HTTPException(500, "module_unavailable")
    r = reports.submit(req.app_id, req.reason, req.details or "", req.reporter_email or "")
    if not r.get("ok"):
        raise HTTPException(400, r.get("error", "submit_failed"))
    return r


@router.get("/open")
def open_reports():
    if reports is None:
        raise HTTPException(500, "module_unavailable")
    return {"ok": True, "reports": reports.list_open()}


@router.get("/for-app/{app_id}")
def for_app(app_id: str):
    if reports is None:
        raise HTTPException(500, "module_unavailable")
    return {"ok": True, "reports": reports.list_for_app(app_id)}


@router.post("/resolve")
def resolve(req: ResolveReq):
    if reports is None:
        raise HTTPException(500, "module_unavailable")
    return reports.resolve(req.id, req.notes or "")
