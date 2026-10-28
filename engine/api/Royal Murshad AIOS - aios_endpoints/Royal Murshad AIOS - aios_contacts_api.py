from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_contacts")
import aios_contacts as c

router = APIRouter(prefix="/api/contacts", tags=["contacts"])

class CreateReq(BaseModel):
    name: str
    phones: str = ""
    emails: str = ""
    company: str = ""
    role: str = ""
    address: str = ""
    tags: str = ""
    notes: str = ""

class UpdateReq(BaseModel):
    name: Optional[str] = None
    phones: Optional[str] = None
    emails: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    address: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None

class SearchReq(BaseModel):
    query: str
    limit: int = 30

@router.get("/stats")
def _stats(): return c.stats()

@router.get("/list")
def _list(limit: int = 200, tag: Optional[str] = None): return c.list_contacts(limit, tag)

@router.get("/tags")
def _tags(): return c.tags()

@router.get("/contact/{cid}")
def _get(cid: int): return c.get(cid)

@router.post("/create")
def _create(req: CreateReq):
    return c.create(req.name, req.phones, req.emails, req.company,
                    req.role, req.address, req.tags, req.notes)

@router.post("/update/{cid}")
def _update(cid: int, req: UpdateReq):
    return c.update(cid, **{k: v for k, v in req.dict().items() if v is not None})

@router.post("/delete/{cid}")
def _delete(cid: int): return c.delete(cid)

@router.post("/search")
def _search(req: SearchReq): return c.search(req.query, req.limit)
