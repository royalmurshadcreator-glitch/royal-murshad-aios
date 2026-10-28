"""
ASG Store — Earnings & Payouts API
Endpoints:
    GET  /api/store/earnings/balance?email=...
    GET  /api/store/earnings/list?email=...
    GET  /api/store/earnings/payouts?email=...
    POST /api/store/earnings/request-payout
    POST /api/store/earnings/record (internal)
    GET  /api/store/earnings/platform-stats
"""
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

sys.path.insert(0, str(Path(r"D:\01_PROJECTS\AIOS\04_MEMORY\aios_memory")))

try:
    import aios_store_earnings as earnings
except ImportError:
    earnings = None

router = APIRouter(prefix="/api/store/earnings", tags=["store-earnings"])


class PayoutReq(BaseModel):
    email: str
    amount_cents: int
    method: Optional[str] = "stripe"


class RecordReq(BaseModel):
    email: str
    app_id: str
    order_id: str
    amount_cents: int


@router.get("/platform-stats")
def platform_stats():
    if earnings is None:
        raise HTTPException(500, "module_unavailable")
    return earnings.platform_stats()


@router.get("/balance")
def balance(email: str):
    if earnings is None:
        raise HTTPException(500, "module_unavailable")
    return earnings.developer_balance(email)


@router.get("/list")
def list_earnings(email: str, limit: int = 50):
    if earnings is None:
        raise HTTPException(500, "module_unavailable")
    return {"ok": True, "earnings": earnings.list_earnings(email, limit)}


@router.get("/payouts")
def list_payouts(email: str):
    if earnings is None:
        raise HTTPException(500, "module_unavailable")
    return {"ok": True, "payouts": earnings.list_payouts(email)}


@router.post("/request-payout")
def request_payout(req: PayoutReq):
    if earnings is None:
        raise HTTPException(500, "module_unavailable")
    r = earnings.request_payout(req.email, req.amount_cents, req.method or "stripe")
    if not r.get("ok"):
        raise HTTPException(400, r.get("error", "payout_failed"))
    return r


@router.post("/record")
def record(req: RecordReq):
    if earnings is None:
        raise HTTPException(500, "module_unavailable")
    return earnings.record_earning(req.email, req.app_id, req.order_id, req.amount_cents)
