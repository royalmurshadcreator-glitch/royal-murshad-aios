"""ROYAL JARVIS - Silence Protocol HTTP API"""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(r"D:\01_PROJECTS\AIOS")
TOOLS = ROOT / "06_TOOLS"
SP_DIR = TOOLS / "silence_protocol"

for _p in (str(SP_DIR), str(TOOLS), str(ROOT)):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

_OUR = ("silence_spec", "silence_collect", "silence_analyze", "silence_chain", "silence_report", "silence_cli")
_sp_norm = str(SP_DIR).replace("\\", "/").lower()
for _n in _OUR:
    _m = sys.modules.get(_n)
    if _m is None:
        continue
    _f = getattr(_m, "__file__", "") or ""
    if _sp_norm not in _f.replace("\\", "/").lower():
        try: del sys.modules[_n]
        except Exception: pass

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/silence", tags=["silence"])


def _sp():
    for _p in (str(SP_DIR), str(TOOLS)):
        if _p in sys.path:
            sys.path.remove(_p)
        sys.path.insert(0, _p)
    import silence_report as r
    import silence_chain as c
    import silence_spec as s
    return {"report": r, "chain": c, "spec": s}


class RunReq(BaseModel):
    source: str = "http"
    note: str | None = None
    persist: bool = True


@router.get("/health")
def silence_health():
    try:
        m = _sp()
        return {
            "ok": True,
            "module": "silence_protocol",
            "schema_version": m["spec"].SCHEMA_VERSION,
            "chain_file": str(m["chain"].CHAIN_FILE),
            "report_module": getattr(m["report"], "__file__", None),
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e)[:300], "trace": traceback.format_exc()[-1200:]}


@router.post("/run")
def silence_run(req: RunReq):
    try:
        return _sp()["report"].generate_report(persist=req.persist, source=req.source, note=req.note)
    except Exception as e:
        import traceback
        raise HTTPException(500, f"run error: {str(e)[:300]} | {traceback.format_exc()[-800:]}")


@router.get("/latest")
def silence_latest():
    try:
        return _sp()["report"].latest_report()
    except Exception as e:
        raise HTTPException(500, f"latest error: {str(e)[:200]}")


@router.get("/list")
def silence_list(limit: int = 20):
    try:
        return _sp()["report"].list_reports(limit=int(limit))
    except Exception as e:
        raise HTTPException(500, f"list error: {str(e)[:200]}")


@router.get("/verify")
def silence_verify():
    try:
        return _sp()["report"].verify()
    except Exception as e:
        raise HTTPException(500, f"verify error: {str(e)[:200]}")


@router.get("/stats")
def silence_stats():
    try:
        return _sp()["report"].stats()
    except Exception as e:
        raise HTTPException(500, f"stats error: {str(e)[:200]}")


print("[silence-protocol] API loaded")
