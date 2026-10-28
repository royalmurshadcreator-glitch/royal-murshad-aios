"""Royal Jarvis — Stomach API router."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import aios_stomach as st

router = APIRouter(prefix="/api/stomach", tags=["stomach"])

class FeedIn(BaseModel):
    source: str = "text"
    content: str
    auto_hypothesize: bool = True

@router.post("/feed")
def feed(req: FeedIn):
    try:
        return st.feed(req.source, req.content, req.auto_hypothesize)
    except Exception as e:
        raise HTTPException(500, f"feed error: {str(e)[:200]}")

@router.get("/stats")
def stats():
    try: return st.stats()
    except Exception as e: raise HTTPException(500, f"stats error: {str(e)[:200]}")

@router.get("/facts")
def list_facts(limit: int = 20):
    try: return {"ok": True, "facts": st.list_facts(limit)}
    except Exception as e: raise HTTPException(500, f"facts error: {str(e)[:200]}")
