from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_slides")
import aios_slides as sl

router = APIRouter(prefix="/api/slides", tags=["slides"])

class CreateReq(BaseModel):
    name: str
    description: str = ""
    slides: Optional[List[Dict[str, Any]]] = None

class UpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    slides: Optional[List[Dict[str, Any]]] = None

@router.get("/stats")
def _stats(): return sl.stats()

@router.get("/list")
def _list(): return sl.list_decks()

@router.get("/deck/{did}")
def _get(did: str): return sl.get(did)

@router.post("/create")
def _create(req: CreateReq): return sl.create(req.name, req.description, req.slides)

@router.post("/update/{did}")
def _update(did: str, req: UpdateReq):
    return sl.update(did, req.name, req.description, req.slides)

@router.post("/delete/{did}")
def _delete(did: str): return sl.delete(did)

@router.get("/export/{did}.pptx")
def _export(did: str):
    r = sl.export_pptx(did)
    if not r.get("ok"):
        return r
    fname = r["name"].replace(" ", "_") + ".pptx"
    return Response(content=r["data"],
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'})
