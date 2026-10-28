"""aios_knowledge — API router."""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_knowledge")
import aios_knowledge as k

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class IndexReq(BaseModel):
    root: str
    limit: int = 500


class QueryReq(BaseModel):
    query: str
    top_k: int = 5


@router.get("/stats")
def stats(): return k.stats()


@router.post("/index")
def index(req: IndexReq, bg: BackgroundTasks):
    # Run synchronously for small batches; background for large
    return k.index_folder(req.root, req.limit)


@router.post("/query")
def query(req: QueryReq): return k.query(req.query, req.top_k)


@router.get("/sources")
def sources(limit: int = 100): return k.list_sources(limit)


@router.post("/rebuild")
def rebuild(): return k.rebuild()
