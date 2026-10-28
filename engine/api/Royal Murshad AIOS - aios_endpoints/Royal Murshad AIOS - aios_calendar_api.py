from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_calendar")
import aios_calendar as c

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

class CreateReq(BaseModel):
    title: str
    start_ts: int
    end_ts: Optional[int] = None
    body: str = ""
    location: str = ""
    tags: str = ""
    all_day: bool = False
    recurring: str = ""

@router.get("/stats")
def _stats(): return c.stats()

@router.get("/list")
def _list(from_ts: Optional[int] = None, to_ts: Optional[int] = None, limit: int = 100):
    return c.list_events(from_ts, to_ts, limit)

@router.get("/today")
def _today(): return c.today()

@router.get("/week")
def _week(): return c.week()

@router.get("/upcoming")
def _upcoming(days: int = 7, limit: int = 50): return c.upcoming(days, limit)

@router.post("/create")
def _create(req: CreateReq):
    return c.create(req.title, req.start_ts, req.end_ts, req.body,
                    req.location, req.tags, req.all_day, req.recurring)

@router.get("/event/{eid}")
def _get(eid: int): return c.get(eid)

@router.post("/delete/{eid}")
def _delete(eid: int): return c.delete(eid)

@router.post("/search")
def _search(q: str, limit: int = 30): return c.search(q, limit)
