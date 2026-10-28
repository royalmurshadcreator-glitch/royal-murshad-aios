"""ROYAL JARVIS - Refusal Negotiation HTTP API (Phase 8, collision-safe)"""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(r"D:\01_PROJECTS\AIOS")
TOOLS = ROOT / "06_TOOLS"
RN_DIR = TOOLS / "refusal_negotiation"

_rn_str = str(RN_DIR)
_tools_str = str(TOOLS)
_root_str = str(ROOT)

for _p in (_rn_str, _tools_str, _root_str):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

_OUR_NAMES = ("rn_spec", "rn_chain", "rn_classify", "rn_alternatives", "rn_report", "rn_cli")
_rn_norm = _rn_str.replace("\\", "/").lower()
for _n in _OUR_NAMES:
    _m = sys.modules.get(_n)
    if _m is None:
        continue
    _f = getattr(_m, "__file__", "") or ""
    if _rn_norm not in _f.replace("\\", "/").lower():
        try:
            del sys.modules[_n]
        except Exception:
            pass

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/refusal-negotiation", tags=["refusal-negotiation"])


def _rn():
    for _p in (_rn_str, _tools_str):
        if _p in sys.path:
            sys.path.remove(_p)
        sys.path.insert(0, _p)
    import rn_report as _report
    import rn_chain as _chain
    import rn_spec as _spec
    import rn_classify as _classify
    import rn_alternatives as _alts
    return {"report": _report, "chain": _chain, "spec": _spec, "classify": _classify, "alts": _alts}


class GuardrailReq(BaseModel):
    pattern: str
    severity: str = "high"
    risk: str = "high"
    snippet: str = ""
    request_text: str = ""
    request_source: str = "http"
    persist: bool = True


class PermissionReq(BaseModel):
    reason: str = "locked"
    resource_id: str | None = None
    action: str | None = None
    request_text: str = ""
    request_source: str = "http"
    persist: bool = True


class ConfirmationReq(BaseModel):
    cancel_reason: str
    task_id: str | None = None
    request_text: str = ""
    request_source: str = "http"
    persist: bool = True


class AppealReq(BaseModel):
    rn_id: str
    note: str = ""


class AlternativesReq(BaseModel):
    reason: str
    resource_id: str | None = None


@router.get("/health")
def rn_health():
    try:
        m = _rn()
        return {
            "ok": True,
            "module": "refusal_negotiation",
            "schema_version": m["spec"].SCHEMA_VERSION,
            "chain_file": str(m["chain"].CHAIN_FILE),
            "report_module": getattr(m["report"], "__file__", None),
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e)[:300], "trace": traceback.format_exc()[-1200:]}


@router.post("/guardrail")
def rn_from_guardrail(req: GuardrailReq):
    try:
        scan = {
            "ok": True, "clean": False, "risk": req.risk,
            "matches": [{"pattern": req.pattern, "severity": req.severity, "snippet": req.snippet}],
        }
        return _rn()["report"].from_guardrail(
            scan, request_text=req.request_text,
            request_source=req.request_source, persist=req.persist)
    except Exception as e:
        import traceback
        raise HTTPException(500, f"guardrail error: {str(e)[:300]} | {traceback.format_exc()[-800:]}")


@router.post("/permission")
def rn_from_permission(req: PermissionReq):
    try:
        perm = {"allowed": False, "reason": req.reason}
        return _rn()["report"].from_permission(
            perm, resource_id=req.resource_id, action=req.action,
            request_text=req.request_text, request_source=req.request_source,
            persist=req.persist)
    except Exception as e:
        import traceback
        raise HTTPException(500, f"permission error: {str(e)[:300]} | {traceback.format_exc()[-800:]}")


@router.post("/confirmation")
def rn_from_confirmation(req: ConfirmationReq):
    try:
        return _rn()["report"].from_confirmation(
            req.cancel_reason, task_id=req.task_id,
            request_text=req.request_text, request_source=req.request_source,
            persist=req.persist)
    except Exception as e:
        import traceback
        raise HTTPException(500, f"confirmation error: {str(e)[:300]} | {traceback.format_exc()[-800:]}")


@router.get("/list")
def rn_list(limit: int = 20):
    try:
        return _rn()["report"].list_records(limit=int(limit))
    except Exception as e:
        raise HTTPException(500, f"list error: {str(e)[:200]}")


@router.get("/get/{rn_id}")
def rn_get(rn_id: str):
    try:
        return _rn()["report"].get(rn_id)
    except Exception as e:
        raise HTTPException(500, f"get error: {str(e)[:200]}")


@router.post("/appeal")
def rn_appeal(req: AppealReq):
    try:
        return _rn()["report"].appeal(req.rn_id, req.note)
    except Exception as e:
        raise HTTPException(500, f"appeal error: {str(e)[:200]}")


@router.post("/alternatives")
def rn_alternatives(req: AlternativesReq):
    try:
        m = _rn()
        raw = {"source": "guardrail", "reason": req.reason, "severity": "high",
               "resource_id": req.resource_id}
        final = m["classify"].finalize(raw)
        return m["alts"].propose_all(final)
    except Exception as e:
        raise HTTPException(500, f"alternatives error: {str(e)[:200]}")


@router.get("/verify")
def rn_verify():
    try:
        return _rn()["report"].verify()
    except Exception as e:
        raise HTTPException(500, f"verify error: {str(e)[:200]}")


@router.get("/stats")
def rn_stats():
    try:
        return _rn()["report"].stats()
    except Exception as e:
        raise HTTPException(500, f"stats error: {str(e)[:200]}")


print("[refusal-negotiation] API loaded (collision-safe)")
