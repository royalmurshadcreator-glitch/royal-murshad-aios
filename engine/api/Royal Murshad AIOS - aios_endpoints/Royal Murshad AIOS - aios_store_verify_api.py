"""
ASG Store — Developer Verification API
Endpoints:
    POST /api/store/verify/submit
    GET  /api/store/verify/status?email=...
    GET  /api/store/verify/pending
    POST /api/store/verify/review
    GET  /api/store/verify/stats
"""
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

sys.path.insert(0, str(Path(r"D:\01_PROJECTS\AIOS\04_MEMORY\aios_memory")))

try:
    import aios_store_verifications as verif
except ImportError:
    verif = None

router = APIRouter(prefix="/api/store/verify", tags=["store-verify"])


class SubmitReq(BaseModel):
    email: str
    full_legal_name: str
    country: str
    id_type: str
    id_number: str
    company_name: Optional[str] = ""
    tax_id: Optional[str] = ""
    phone: Optional[str] = ""
    notes: Optional[str] = ""


class ReviewReq(BaseModel):
    id: str
    approve: bool
    notes: Optional[str] = ""


@router.get("/stats")
def stats():
    if verif is None:
        raise HTTPException(500, "module_unavailable")
    return verif.stats()


@router.post("/submit")
def submit(req: SubmitReq):
    if verif is None:
        raise HTTPException(500, "module_unavailable")
    r = verif.submit_verification(
        req.email, req.full_legal_name, req.country,
        req.id_type, req.id_number,
        req.company_name or "", req.tax_id or "", req.phone or "", req.notes or ""
    )
    if not r.get("ok"):
        raise HTTPException(400, r.get("error", "submit_failed"))
    return r


@router.get("/status")
def status(email: str):
    if verif is None:
        raise HTTPException(500, "module_unavailable")
    return verif.get_status(email)


@router.get("/pending")
def pending():
    if verif is None:
        raise HTTPException(500, "module_unavailable")
    return {"ok": True, "pending": verif.list_pending()}


@router.post("/review")
def review(req: ReviewReq):
    if verif is None:
        raise HTTPException(500, "module_unavailable")
    return verif.review(req.id, req.approve, req.notes or "")
