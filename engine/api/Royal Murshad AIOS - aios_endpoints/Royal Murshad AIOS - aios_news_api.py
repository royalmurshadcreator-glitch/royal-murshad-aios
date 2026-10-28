from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_news")
import aios_news as n

router = APIRouter(prefix="/api/news", tags=["news"])

class FeedReq(BaseModel):
    url: str
    title: str = ""
    category: str = ""

class SearchReq(BaseModel):
    query: str
    limit: int = 30

@router.get("/stats")
def _stats(): return n.stats()

@router.get("/feeds")
def _feeds(): return n.list_feeds()

@router.post("/feeds/new")
def _new_feed(req: FeedReq): return n.add_feed(req.url, req.title, req.category)

@router.post("/feeds/{fid}/delete")
def _del_feed(fid: int): return n.delete_feed(fid)

@router.post("/feeds/{fid}/fetch")
def _fetch_feed(fid: int, limit: int = 50): return n.fetch_feed(fid, limit)

@router.post("/fetch-all")
def _fetch_all(): return n.fetch_all()

@router.get("/items")
def _items(limit: int = 50, feed_id: Optional[int] = None,
           unread_only: bool = False, starred_only: bool = False):
    return n.list_items(limit, feed_id, unread_only, starred_only)

@router.get("/item/{iid}")
def _item(iid: str): return n.get_item(iid)

@router.post("/item/{iid}/read")
def _read(iid: str, read: bool = True): return n.mark_read(iid, read)

@router.post("/item/{iid}/star")
def _star(iid: str, starred: bool = True): return n.star_item(iid, starred)

@router.post("/search")
def _search(req: SearchReq): return n.search(req.query, req.limit)
