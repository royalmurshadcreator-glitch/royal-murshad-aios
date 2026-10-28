"""ROYAL JARVIS - Causal Diary HTTP API (Phase 6, collision-safe)"""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(r"D:\\01_PROJECTS\\AIOS")
TOOLS = ROOT / "06_TOOLS"
CD_DIR = TOOLS / "causal_diary"

_cd_str = str(CD_DIR)
_tools_str = str(TOOLS)
_root_str = str(ROOT)

for _p in (_cd_str, _tools_str, _root_str):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

_OUR_NAMES = ("causal_diary_spec", "causal_diary_chain", "causal_diary_collect", "causal_diary_build", "causal_diary_report", "causal_diary_cli")
_cd_norm = _cd_str.replace("\\", "/").lower()
for _n in _OUR_NAMES:
    _m = sys.modules.get(_n)
    if _m is None:
        continue
    _f = getattr(_m, "__file__", "") or ""
    if _cd_norm not in _f.replace("\\", "/").lower():
        try:
            del sys.modules[_n]
        except Exception:
            pass

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/causal-diary", tags=["causal-diary"])


def _cd():
    for _p in (_cd_str, _tools_str):
        if _p in sys.path:
            sys.path.remove(_p)
        sys.path.insert(0, _p)
    import causal_diary_report as _report
    import causal_diary_chain as _chain
    import causal_diary_spec as _spec
    import causal_diary_collect as _collect
    return {"report": _report, "chain": _chain, "spec": _spec, "collect": _collect}


class WriteReq(BaseModel):
    question_text: str
    chosen_action: str
    chosen_rationale: str = ""
    decision_kind: str = "custom"
    constraints: list[str] = []
    assumptions: list[str] = []
    uncertainty: list[str] = []
    reviewer_kind: str = "unreviewed"
    reviewer_note: str = ""
    source: str = "http"
    persist: bool = True
    with_alternatives: bool = False
    with_world_prediction: bool = False
    with_verifier: bool = False


class GetReq(BaseModel):
    diary_id: str


class OutcomeReq(BaseModel):
    diary_id: str
    outcome: str
    note: str | None = None


@router.get("/health")
def causal_diary_health():
    try:
        m = _cd()
        return {
            "ok": True,
            "module": "causal_diary",
            "schema_version": m["spec"].SCHEMA_VERSION,
            "chain_file": str(m["chain"].CHAIN_FILE),
            "report_module": getattr(m["report"], "__file__", None),
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e)[:300], "trace": traceback.format_exc()[-1200:]}


@router.post("/write")
def causal_diary_write(req: WriteReq):
    try:
        return _cd()["report"].write_entry(
            question_text=req.question_text,
            chosen_action=req.chosen_action,
            chosen_rationale=req.chosen_rationale,
            decision_kind=req.decision_kind,
            constraints=req.constraints,
            assumptions=req.assumptions,
            uncertainty=req.uncertainty,
            reviewer_kind=req.reviewer_kind,
            reviewer_note=req.reviewer_note,
            source=req.source,
            persist=req.persist,
            with_alternatives=req.with_alternatives,
            with_world_prediction=req.with_world_prediction,
            with_verifier=req.with_verifier,
        )
    except Exception as e:
        import traceback
        raise HTTPException(500, f"write error: {str(e)[:300]} | {traceback.format_exc()[-800:]}")


@router.get("/list")
def causal_diary_list(limit: int = 20):
    try:
        return _cd()["report"].list_entries(limit=int(limit))
    except Exception as e:
        raise HTTPException(500, f"list error: {str(e)[:200]}")


@router.post("/get")
def causal_diary_get(req: GetReq):
    try:
        return _cd()["report"].get_entry(req.diary_id)
    except Exception as e:
        raise HTTPException(500, f"get error: {str(e)[:200]}")


@router.post("/outcome")
def causal_diary_outcome(req: OutcomeReq):
    try:
        return _cd()["report"].set_outcome(req.diary_id, req.outcome, note=req.note)
    except Exception as e:
        raise HTTPException(500, f"outcome error: {str(e)[:200]}")


@router.get("/verify")
def causal_diary_verify():
    try:
        return _cd()["report"].verify()
    except Exception as e:
        raise HTTPException(500, f"verify error: {str(e)[:200]}")


@router.get("/stats")
def causal_diary_stats():
    try:
        return _cd()["report"].stats()
    except Exception as e:
        raise HTTPException(500, f"stats error: {str(e)[:200]}")


@router.get("/snapshot")
def causal_diary_snapshot():
    try:
        return _cd()["report"].snapshot()
    except Exception as e:
        raise HTTPException(500, f"snapshot error: {str(e)[:200]}")


print("[causal-diary] API loaded (collision-safe)")

