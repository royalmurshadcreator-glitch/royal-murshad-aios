"""Royal Jarvis — eSIM API router."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import aios_esim_bridge as esim

router = APIRouter(prefix="/api/esim", tags=["esim"])

class RunIn(BaseModel):
    name: str
    args: list[str] = []
    timeout: int = 30

@router.get("/health")
def health():
    try: return esim.health()
    except Exception as e: raise HTTPException(500, str(e)[:200])

@router.get("/tools")
def tools():
    try: return esim.tools()
    except Exception as e: raise HTTPException(500, str(e)[:200])

@router.get("/inventory")
def inventory():
    try: return esim.file_inventory()
    except Exception as e: raise HTTPException(500, str(e)[:200])

@router.post("/run")
def run(req: RunIn):
    try:
        return esim.run_tool(req.name, req.args, req.timeout)
    except Exception as e:
        raise HTTPException(500, str(e)[:200])