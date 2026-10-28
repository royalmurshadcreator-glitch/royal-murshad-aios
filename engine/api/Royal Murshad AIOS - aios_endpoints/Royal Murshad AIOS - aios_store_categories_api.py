"""
ASG Store — Categories & Search API
Endpoints:
    GET  /api/store/categories/list
    POST /api/store/categories/set
    GET  /api/store/categories/app/{app_id}
    POST /api/store/categories/filter
    GET  /api/store/categories/stats
"""
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict

sys.path.insert(0, str(Path(r"D:\01_PROJECTS\AIOS\04_MEMORY\aios_memory")))

try:
    import aios_store_categories as categories
except ImportError:
    categories = None

router = APIRouter(prefix="/api/store/categories", tags=["store-categories"])


class SetCategoryReq(BaseModel):
    app_id: str
    category_id: str


class FilterReq(BaseModel):
    apps: List[Dict]
    query: Optional[str] = None
    category_id: Optional[str] = None
    max_price: Optional[float] = None
    min_rating: Optional[str] = None
    user_max_rating: Optional[str] = None


@router.get("/list")
def list_categories():
    if categories is None:
        raise HTTPException(500, "module_unavailable")
    return {"ok": True, "categories": categories.list_categories()}


@router.post("/set")
def set_category(req: SetCategoryReq):
    if categories is None:
        raise HTTPException(500, "module_unavailable")
    r = categories.set_app_category(req.app_id, req.category_id)
    if not r.get("ok"):
        raise HTTPException(400, r.get("error", "set_failed"))
    return r


@router.get("/app/{app_id}")
def get_app_category(app_id: str):
    if categories is None:
        raise HTTPException(500, "module_unavailable")
    return categories.get_app_category(app_id)


@router.post("/filter")
def filter_apps(req: FilterReq):
    if categories is None:
        raise HTTPException(500, "module_unavailable")
    filtered = categories.filter_apps(
        req.apps,
        query=req.query,
        category_id=req.category_id,
        max_price=req.max_price,
        min_rating=req.min_rating,
        user_max_rating=req.user_max_rating
    )
    return {"ok": True, "apps": filtered}


@router.get("/stats")
def stats():
    if categories is None:
        raise HTTPException(500, "module_unavailable")
    return categories.stats()
