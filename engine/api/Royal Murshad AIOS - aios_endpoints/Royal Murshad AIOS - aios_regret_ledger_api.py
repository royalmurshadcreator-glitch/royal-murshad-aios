"""ROYAL JARVIS - Regret Ledger HTTP API (Phase 9, collision-safe)"""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(r"D:\01_PROJECTS\AIOS")
TOOLS = ROOT / "06_TOOLS"
RL_DIR = TOOLS / "regret_ledger"

_rl_str = str(RL_DIR)
_tools_str = str(TOOLS)
_root_str = str(ROOT)

for _p in (_rl_str, _tools_str, _root_str):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

_OUR_NAMES = ("regret_spec", "regret_chain", "regret_collect", "regret_analyze", "regret_report", "regret_cli")
_rl_norm = _rl_str.replace("\\", "/").lower()
for _n in _OUR_NAMES:
    _m = sys.modules.get(_n)
    if _m is None:
        continue
    _f = getattr(_m, "__file__", "") or ""
    if _rl_norm not in _f.replace("\\", "/").lower():
        try:
            del sys.modules[_n]
        except Exception:
            pass

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/regret-ledger", tags=["regret-ledger"])


def _rl():
    for _p in (_rl_str, _tools_str):
        if _p in sys.path:
            sys.path.remove(_p)
        sys.path.insert(0, _p)
    import regret_report as _report
    import regret_chain as _chain
    import regret_spec as _spec
    import regret_analyze as _analyze
    import regret_collect as _collect
    return {"report": _report, "chain": _chain, "spec": _spec,
            "analyze": _analyze, "collect": _collect}


class DecisionReq(BaseModel):
    decision_kind: str = "task_execution"
    command: str
    risk_level: str
    chosen: dict | None = None
    counterfactual: dict | None = None
    source: str = "http"
    persist: bool = True


class OutcomeReq(BaseModel):
    decision_ref: str
    outcome_kind: str
    note: str = ""
    source: str = "http"
    persist: bool = True


class ComputeReq(BaseModel):
    decision_ref: str
    persist: bool = True


class IngestReq(BaseModel):
    persist: bool = True


@router.get("/health")
def rl_health():
    try:
        m = _rl()
        return {
            "ok": True,
            "module": "regret_ledger",
            "schema_version": m["spec"].SCHEMA_VERSION,
            "chain_file": str(m["chain"].CHAIN_FILE),
            "report_module": getattr(m["report"], "__file__", None),
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e)[:300], "trace": traceback.format_exc()[-1200:]}


@router.post("/decision")
def rl_decision(req: DecisionReq):
    try:
        return _rl()["report"].record_decision(
            decision_kind=req.decision_kind,
            command=req.command,
            risk_level=req.risk_level,
            chosen=req.chosen or {},
            counterfactual=req.counterfactual,
            source=req.source,
            persist=req.persist,
        )
    except Exception as e:
        import traceback
        raise HTTPException(500, f"decision error: {str(e)[:300]} | {traceback.format_exc()[-800:]}")


@router.post("/outcome")
def rl_outcome(req: OutcomeReq):
    try:
        return _rl()["report"].record_outcome(
            decision_ref=req.decision_ref,
            outcome_kind=req.outcome_kind,
            note=req.note,
            source=req.source,
            persist=req.persist,
        )
    except Exception as e:
        raise HTTPException(500, f"outcome error: {str(e)[:200]}")


@router.post("/compute")
def rl_compute(req: ComputeReq):
    try:
        return _rl()["report"].compute_for(req.decision_ref, persist=req.persist)
    except Exception as e:
        raise HTTPException(500, f"compute error: {str(e)[:200]}")


@router.post("/ingest-orchestrator")
def rl_ingest(req: IngestReq):
    try:
        return _rl()["report"].ingest_orchestrator_tasks(persist=req.persist)
    except Exception as e:
        import traceback
        raise HTTPException(500, f"ingest error: {str(e)[:300]} | {traceback.format_exc()[-800:]}")


@router.get("/list")
def rl_list(limit: int = 50, type: str | None = None):
    try:
        return _rl()["report"].list_records(limit=int(limit), type_filter=type)
    except Exception as e:
        raise HTTPException(500, f"list error: {str(e)[:200]}")


@router.get("/get/{rl_id}")
def rl_get(rl_id: str):
    try:
        return _rl()["report"].get(rl_id)
    except Exception as e:
        raise HTTPException(500, f"get error: {str(e)[:200]}")


@router.get("/verify")
def rl_verify():
    try:
        return _rl()["report"].verify()
    except Exception as e:
        raise HTTPException(500, f"verify error: {str(e)[:200]}")


@router.get("/stats")
def rl_stats():
    try:
        return _rl()["report"].stats()
    except Exception as e:
        raise HTTPException(500, f"stats error: {str(e)[:200]}")


print("[regret-ledger] API loaded (collision-safe)")
