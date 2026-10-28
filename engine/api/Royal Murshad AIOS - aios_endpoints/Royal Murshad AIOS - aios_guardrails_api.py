from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_guardrails")
import aios_guardrails_runtime as g

router = APIRouter(prefix="/api/guardrails", tags=["guardrails"])

class CheckReq(BaseModel):
    agent_id: str
    endpoint: str

class RegisterReq(BaseModel):
    agent_id: str
    kind: str
    scopes: List[str] = []

@router.get("/status")
def _status(): return g.status()

@router.get("/agents")
def _agents(): return g.list_agents()

@router.post("/seed")
def _seed(): return g.seed_defaults()

@router.post("/register")
def _register(req: RegisterReq): return g.register(req.agent_id, req.kind, req.scopes)

@router.post("/check")
def _check(req: CheckReq): return g.check(req.agent_id, req.endpoint)

@router.post("/kill")
def _kill(agent_id: Optional[str] = None): return g.kill(agent_id)

@router.post("/revive")
def _revive(agent_id: Optional[str] = None): return g.revive(agent_id)

@router.get("/audit")
def _audit(limit: int = 50): return g.audit_tail(limit)
