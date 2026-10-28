from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_maps")
import aios_maps as m

router = APIRouter(prefix="/api/maps", tags=["maps"])

class PlaceReq(BaseModel):
    name: str
    latitude: float
    longitude: float
    address: str = ""
    category: str = ""
    notes: str = ""
    tags: str = ""
    favorite: bool = False

class UpdatePlaceReq(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[str] = None
    favorite: Optional[bool] = None

class RouteSaveReq(BaseModel):
    name: str
    from_id: str
    to_id: str

class SearchReq(BaseModel):
    query: str
    limit: int = 30

@router.get("/stats")
def _stats(): return m.stats()

@router.get("/places")
def _places(category: Optional[str] = None, favorite_only: bool = False, limit: int = 200):
    return m.list_places(category, favorite_only, limit)

@router.post("/places/new")
def _add(req: PlaceReq):
    return m.add_place(req.name, req.latitude, req.longitude, req.address,
                       req.category, req.notes, req.tags, req.favorite)

@router.get("/place/{pid}")
def _get(pid: str): return m.get_place(pid)

@router.post("/place/{pid}/update")
def _update(pid: str, req: UpdatePlaceReq):
    return m.update_place(pid, **{k: v for k, v in req.dict().items() if v is not None})

@router.post("/place/{pid}/delete")
def _delete(pid: str): return m.delete_place(pid)

@router.get("/nearby/{pid}")
def _nearby(pid: str, radius_km: float = 5.0, limit: int = 20):
    return m.nearby(pid, radius_km, limit)

@router.get("/distance")
def _distance(from_id: str, to_id: str): return m.distance(from_id, to_id)

@router.get("/route")
def _route(from_id: str, to_id: str): return m.route(from_id, to_id)

@router.post("/routes/save")
def _save_route(req: RouteSaveReq): return m.save_route(req.name, req.from_id, req.to_id)

@router.get("/routes")
def _routes(): return m.list_saved_routes()

@router.post("/routes/{rid}/delete")
def _del_route(rid: str): return m.delete_saved_route(rid)

@router.get("/categories")
def _cats(): return m.categories()

@router.post("/search")
def _search(req: SearchReq): return m.search(req.query, req.limit)
