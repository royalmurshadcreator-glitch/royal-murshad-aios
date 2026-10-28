from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_photos")
import aios_photos as p

router = APIRouter(prefix="/api/photos", tags=["photos"])

class IndexReq(BaseModel):
    root: str
    limit: int = 500

class SearchReq(BaseModel):
    query: str
    limit: int = 30

class TagReq(BaseModel):
    tags: str

@router.get("/stats")
def _stats(): return p.stats()

@router.get("/list")
def _list(limit: int = 100, tag: Optional[str] = None): return p.list_photos(limit, tag)

@router.get("/photo/{pid}")
def _get(pid: int): return p.get(pid)

@router.post("/index")
def _index(req: IndexReq): return p.index_folder(req.root, req.limit)

@router.post("/search")
def _search(req: SearchReq): return p.search(req.query, req.limit)

@router.post("/tag/{pid}")
def _tag(pid: int, req: TagReq): return p.tag(pid, req.tags)

@router.get("/duplicates")
def _dupes(): return p.duplicates()
