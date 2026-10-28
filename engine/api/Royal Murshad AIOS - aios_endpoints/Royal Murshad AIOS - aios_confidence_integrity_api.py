"""ROYAL JARVIS - Confidence Integrity HTTP API (Phase 7, collision-safe)"""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(r"D:\\01_PROJECTS\\AIOS")
TOOLS = ROOT / "06_TOOLS"
CI_DIR = TOOLS / "confidence_integrity"

_ci_str = str(CI_DIR)
_tools_str = str(TOOLS)
_root_str = str(ROOT)

for _p in (_ci_str, _tools_str, _root_str):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

_OUR_NAMES = ("ci_spec", "ci_chain", "ci_collect", "ci_analyze", "ci_report", "ci_cli")
_ci_norm = _ci_str.replace("\\", "/").lower()
for _n in _OUR_NAMES:
    _m = sys.modules.get(_n)
    if _m is None:
        continue
    _f = getattr(_m, "__file__", "") or ""
    if _ci_norm not in _f.replace("\\", "/").lower():
        try:
            del sys.modules[_n]
        except Exception:
            pass

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/confidence-integrity", tags=["confidence-integrity"])


def _ci():
    for _p in (_ci_str, _tools_str):
        if _p in sys.path:
            sys.path.remove(_p)
        sys.path.insert(0, _p)
    import ci_report as _report
    import ci_chain as _chain
    import ci_spec as _spec
    import ci_collect as _collect
    return {"report": _report, "chain": _chain, "spec": _spec, "collect": _collect}


class RunReq(BaseModel):
    source: str = "http"
    note: str | None = None
    persist: bool = True
    verifier_limit: int = 50
    metacog_limit: int = 50
    diary_limit: int = 200
    cross_model_question: str | None = None
    cross_model_response: str | None = None


class ProbeReq(BaseModel):
    question: str
    response: str


@router.get("/health")
def ci_health():
    try:
        m = _ci()
        return {
            "ok": True,
            "module": "confidence_integrity",
            "schema_version": m["spec"].SCHEMA_VERSION,
            "chain_file": str(m["chain"].CHAIN_FILE),
            "report_module": getattr(m["report"], "__file__", None),
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e)[:300], "trace": traceback.format_exc()[-1200:]}


@router.post("/run")
def ci_run(req: RunReq):
    try:
        return _ci()["report"].generate_report(
            persist=req.persist,
            source=req.source,
            note=req.note,
            verifier_limit=req.verifier_limit,
            metacog_limit=req.metacog_limit,
            diary_limit=req.diary_limit,
            cross_model_question=req.cross_model_question,
            cross_model_response=req.cross_model_response,
        )
    except Exception as e:
        import traceback
        raise HTTPException(500, f"run error: {str(e)[:300]} | {traceback.format_exc()[-800:]}")


@router.get("/latest")
def ci_latest():
    try:
        return _ci()["report"].latest_report()
    except Exception as e:
        raise HTTPException(500, f"latest error: {str(e)[:200]}")


@router.get("/list")
def ci_list(limit: int = 20):
    try:
        return _ci()["report"].list_reports(limit=int(limit))
    except Exception as e:
        raise HTTPException(500, f"list error: {str(e)[:200]}")


@router.get("/verify")
def ci_verify():
    try:
        return _ci()["report"].verify()
    except Exception as e:
        raise HTTPException(500, f"verify error: {str(e)[:200]}")


@router.get("/stats")
def ci_stats():
    try:
        return _ci()["report"].stats()
    except Exception as e:
        raise HTTPException(500, f"stats error: {str(e)[:200]}")


@router.post("/probe")
def ci_probe(req: ProbeReq):
    try:
        return _ci()["report"].probe(req.question, req.response)
    except Exception as e:
        import traceback
        raise HTTPException(500, f"probe error: {str(e)[:300]} | {traceback.format_exc()[-800:]}")


print("[confidence-integrity] API loaded (collision-safe)")
