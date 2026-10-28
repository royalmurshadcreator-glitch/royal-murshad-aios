from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_forum")
import aios_forum as f

router = APIRouter(prefix="/api/forum", tags=["forum"])

class BoardReq(BaseModel):
    name: str
    description: str = ""

class TopicReq(BaseModel):
    board_id: str
    title: str
    body: str = ""
    author: Optional[str] = None
    tags: str = ""

class ReplyReq(BaseModel):
    body: str
    author: Optional[str] = None

class UpdateReq(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    tags: Optional[str] = None
    pinned: Optional[bool] = None
    locked: Optional[bool] = None

class SearchReq(BaseModel):
    query: str
    limit: int = 30

@router.get("/stats")
def _stats(): return f.stats()

@router.get("/boards")
def _boards(): return f.list_boards()

@router.post("/boards/new")
def _new_board(req: BoardReq): return f.create_board(req.name, req.description)

@router.get("/board/{bid}")
def _board(bid: str): return f.get_board(bid)

@router.post("/board/{bid}/delete")
def _del_board(bid: str): return f.delete_board(bid)

@router.get("/board/{bid}/topics")
def _topics(bid: str, limit: int = 100): return f.list_topics(bid, limit)

@router.post("/topics/new")
def _new_topic(req: TopicReq):
    return f.create_topic(req.board_id, req.title, req.body, req.author, req.tags)

@router.get("/topic/{tid}")
def _topic(tid: str): return f.get_topic(tid)

@router.post("/topic/{tid}/reply")
def _reply(tid: str, req: ReplyReq): return f.reply(tid, req.body, req.author)

@router.post("/topic/{tid}/update")
def _update(tid: str, req: UpdateReq):
    return f.update_topic(tid, **{k: v for k, v in req.dict().items() if v is not None})

@router.post("/topic/{tid}/delete")
def _del_topic(tid: str): return f.delete_topic(tid)

@router.post("/reply/{rid}/delete")
def _del_reply(rid: str): return f.delete_reply(rid)

@router.post("/search")
def _search(req: SearchReq): return f.search(req.query, req.limit)
