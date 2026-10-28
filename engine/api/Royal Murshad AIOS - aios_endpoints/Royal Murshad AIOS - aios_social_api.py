from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_social")
import aios_social as s

router = APIRouter(prefix="/api/social", tags=["social"])

class PostReq(BaseModel):
    body: str
    author: Optional[str] = None
    tags: str = ""
    status: str = "published"
    parent_id: Optional[str] = None

class PostUpdateReq(BaseModel):
    body: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[str] = None

class FollowReq(BaseModel):
    identity: str
    display_name: str = ""
    kind: str = "person"
    url: str = ""
    notes: str = ""

class SearchReq(BaseModel):
    query: str
    limit: int = 30

@router.get("/stats")
def _stats(): return s.stats()

@router.get("/feed")
def _feed(limit: int = 50, author: Optional[str] = None,
          tag: Optional[str] = None, include_drafts: bool = False):
    return s.feed(limit, author, tag, include_drafts)

@router.post("/posts/new")
def _new(req: PostReq):
    return s.post(req.body, req.author, req.tags, req.status, req.parent_id)

@router.get("/post/{pid}")
def _get(pid: str): return s.get_post(pid)

@router.get("/post/{pid}/thread")
def _thread(pid: str): return s.thread(pid)

@router.post("/post/{pid}/update")
def _update(pid: str, req: PostUpdateReq):
    return s.update_post(pid, **{k: v for k, v in req.dict().items() if v is not None})

@router.post("/post/{pid}/delete")
def _del(pid: str): return s.delete_post(pid)

@router.post("/post/{pid}/like")
def _like(pid: str): return s.like(pid)

@router.post("/post/{pid}/unlike")
def _unlike(pid: str): return s.unlike(pid)

@router.get("/follows")
def _follows(kind: Optional[str] = None): return s.list_follows(kind)

@router.post("/follow")
def _follow(req: FollowReq):
    return s.follow(req.identity, req.display_name, req.kind, req.url, req.notes)

@router.post("/unfollow/{identity}")
def _unfollow(identity: str): return s.unfollow(identity)

@router.get("/tags")
def _tags(): return s.tags()

@router.post("/search")
def _search(req: SearchReq): return s.search(req.query, req.limit)
