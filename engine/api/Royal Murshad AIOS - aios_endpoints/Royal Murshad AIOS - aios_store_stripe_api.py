"""
ASG Store — Stripe API
Endpoints:
    POST /api/store/stripe/create-session
    POST /api/store/stripe/webhook
    GET  /api/store/stripe/status
    GET  /api/store/stripe/order/{session_id}
    GET  /api/store/stripe/orders?email=...
"""
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(r"D:\01_PROJECTS\AIOS\04_MEMORY\aios_memory")))

try:
    import aios_store_stripe as store_stripe
except ImportError:
    store_stripe = None

router = APIRouter(prefix="/api/store/stripe", tags=["store-stripe"])


class CartItem(BaseModel):
    id: str
    name: str
    tagline: Optional[str] = ""
    price: float


class CreateSessionReq(BaseModel):
    email: str
    items: List[CartItem]
    success_url: str
    cancel_url: str


@router.get("/status")
def status():
    if store_stripe is None:
        return {"ok": False, "error": "module_not_loaded"}
    return store_stripe.stats()


@router.post("/create-session")
def create_session(req: CreateSessionReq):
    if store_stripe is None:
        raise HTTPException(500, "stripe_module_not_available")
    if not store_stripe.is_available():
        raise HTTPException(400, "stripe_not_configured_add_key_to_env")

    items = [i.dict() for i in req.items]
    r = store_stripe.create_checkout_session(
        user_email=req.email,
        items=items,
        success_url=req.success_url,
        cancel_url=req.cancel_url
    )
    if not r.get("ok"):
        raise HTTPException(400, r.get("error", "session_failed"))
    return r


@router.post("/webhook")
async def webhook(request: Request, stripe_signature: Optional[str] = Header(None)):
    if store_stripe is None:
        raise HTTPException(500, "module_unavailable")
    payload = await request.body()
    if not stripe_signature:
        raise HTTPException(400, "missing_signature")

    r = store_stripe.verify_webhook(payload, stripe_signature)
    if not r.get("ok"):
        raise HTTPException(400, "invalid_signature")

    event = r["event"]
    event_type = event.get("type") if isinstance(event, dict) else event.type

    if event_type == "checkout.session.completed":
        data = event["data"]["object"] if isinstance(event, dict) else event.data.object
        session_id = data["id"] if isinstance(data, dict) else data.id
        store_stripe.mark_paid(session_id)

    return {"ok": True}


@router.get("/order/{session_id}")
def get_order(session_id: str):
    if store_stripe is None:
        raise HTTPException(500, "module_unavailable")
    o = store_stripe.get_order_by_session(session_id)
    if not o:
        raise HTTPException(404, "order_not_found")
    return {"ok": True, "order": o}


@router.get("/orders")
def list_orders(email: str):
    if store_stripe is None:
        raise HTTPException(500, "module_unavailable")
    return {"ok": True, "orders": store_stripe.list_user_orders(email)}
