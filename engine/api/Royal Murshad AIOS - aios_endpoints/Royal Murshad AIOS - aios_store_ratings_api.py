"""
ASG Store — Ratings & Parental Controls API
Endpoints:
    POST /api/store/ratings/set
    GET  /api/store/ratings/app/{app_id}
    GET  /api/store/ratings/all
    GET  /api/store/ratings/parental?user_id=...
    POST /api/store/ratings/parental/set
    POST /api/store/ratings/parental/verify-pin
    POST /api/store/ratings/parental/filter
    GET  /api/store/ratings/stats
"""
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict

sys.path.insert(0, str(Path(r"D:\01_PROJECTS\AIOS\04_MEMORY\aios_memory")))

try:
    import aios_store_ratings as ratings
except ImportError:
    ratings = None

router = APIRouter(prefix="/api/store/ratings", tags=["store-ratings"])


class SetRatingReq(BaseModel):
    app_id: str
    rating: str
    descriptors: Optional[List[str]] = []
    notes: Optional[str] = ""


class SetParentalReq(BaseModel):
    user_id: str
    max_rating: Optional[str] = None
    pin: Optional[str] = None
    locked: Optional[bool] = None


class VerifyPinReq(BaseModel):
    user_id: str
    pin: str


class FilterReq(BaseModel):
    user_id: str
    apps: List[Dict]


@router.get("/stats")
def stats():
    if ratings is None:
        raise HTTPException(500, "module_unavailable")
    return ratings.stats()


@router.post("/set")
def set_rating(req: SetRatingReq):
    if ratings is None:
        raise HTTPException(500, "module_unavailable")
    r = ratings.set_app_rating(req.app_id, req.rating, req.descriptors or [], req.notes or "")
    if not r.get("ok"):
        raise HTTPException(400, r.get("error", "set_failed"))
    return r


@router.get("/app/{app_id}")
def get_app_rating(app_id: str):
    if ratings is None:
        raise HTTPException(500, "module_unavailable")
    return ratings.get_app_rating(app_id)


@router.get("/all")
def list_all():
    if ratings is None:
        raise HTTPException(500, "module_unavailable")
    return {"ok": True, "ratings": ratings.list_all_ratings()}


@router.get("/parental")
def get_parental(user_id: str):
    if ratings is None:
        raise HTTPException(500, "module_unavailable")
    return ratings.get_parental(user_id)


@router.post("/parental/set")
def set_parental(req: SetParentalReq):
    if ratings is None:
        raise HTTPException(500, "module_unavailable")
    r = ratings.set_parental(req.user_id, req.max_rating, req.pin, req.locked)
    if not r.get("ok"):
        raise HTTPException(400, r.get("error", "set_failed"))
    return r


@router.post("/parental/verify-pin")
def verify_pin(req: VerifyPinReq):
    if ratings is None:
        raise HTTPException(500, "module_unavailable")
    return ratings.verify_pin(req.user_id, req.pin)


@router.post("/parental/filter")
def filter_apps(req: FilterReq):
    if ratings is None:
        raise HTTPException(500, "module_unavailable")
    return {"ok": True, "apps": ratings.filter_apps_for_age(req.apps, req.user_id)}
