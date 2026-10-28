from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Speech engine import placed safely after __future__
# Lazy import to break circular dependency with aios_master_control
def speak_async(*args, **kwargs):
    from aios_master_control import speak_async as _sa
    return _sa(*args, **kwargs)

# --- Phase A: guardrails loader ---
import sys as _guard_sys
_GUARD_TOOLS = r"D:\\01_PROJECTS\\AIOS\\06_TOOLS"
if _GUARD_TOOLS not in _guard_sys.path:
    _guard_sys.path.insert(0, _GUARD_TOOLS)
try:
    from aios_guardrails import scan_input as _guard_scan
    _GUARD_OK = True
except Exception as _guard_err:
    print(f"[guardrails] failed to load: {_guard_err}")
    _GUARD_OK = False
# --- end guardrails loader ---

router = APIRouter()

ROOT = Path(r"D:\\01_PROJECTS\\AIOS")
ORCH_DIR = Path(r"D:\\01_PROJECTS\\AIOS\\RoyalJarvisOrchestrator")
SHIM = Path(r"D:\\01_PROJECTS\\AIOS\\RoyalJarvisOrchestrator\shim_server.cjs")
LOG_DIR = ROOT / "Logs" / "command_center"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "events.jsonl"
TASKS_FILE = ROOT / "data" / "orchestrator" / "tasks.json"

ORCH_BASE = "http://127.0.0.1:9100"
_LOCK = threading.Lock()
_PROC: Optional[subprocess.Popen] = None
_LOG: list[dict[str, Any]] = []
_STARTED = time.time()


def _log(level: str, kind: str, **payload: Any) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "kind": kind,
        **payload,
    }
    _LOG.append(entry)
    if len(_LOG) > 300:
        del _LOG[:-300]
    try:
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _ensure_orchestrator() -> None:
    global _PROC
    with _LOCK:
        if _PROC is not None and _PROC.poll() is None:
            return
        if not SHIM.exists():
            raise HTTPException(503, f"Missing shim: {SHIM}")
        _PROC = subprocess.Popen(
            ["node", str(SHIM)],
            cwd=str(ORCH_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )

    for _ in range(50):
        try:
            r = requests.get(f"{ORCH_BASE}/api/orchestrator/status", timeout=0.4)
            if r.status_code == 200:
                _log("info", "orchestrator_up", pid=_PROC.pid if _PROC else None)
                return
        except requests.RequestException:
            time.sleep(0.2)

    raise HTTPException(503, "Orchestrator shim failed to become ready on :9100")


def _call(method: str, path: str, body: Optional[dict] = None, timeout: float = 30.0) -> Any:
    _ensure_orchestrator()
    url = f"{ORCH_BASE}{path}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=timeout)
        else:
            r = requests.post(url, json=body or {}, timeout=timeout)
    except requests.RequestException as exc:
        raise HTTPException(502, f"Orchestrator transport error: {exc}") from exc

    text = r.text or ""
    if r.status_code >= 400:
        raise HTTPException(r.status_code, text[:800])
    if not text:
        return {}
    try:
        return r.json()
    except Exception:
        return {"raw": text[:800]}


class CommandSubmit(BaseModel):
    command: str = Field(min_length=1, max_length=2000)
    source: str = "dashboard"
    priority: int = 10
    risk_level: Optional[str] = None
    requires_confirmation: Optional[bool] = None
    parent_task_id: Optional[str] = None
    metadata: Optional[dict] = None


class ConfirmBody(BaseModel):
    task_id: str
    approved: bool = True
    note: Optional[str] = None
    decided_by: str = "boss"


class CancelBody(BaseModel):
    task_id: str
    reason: str = "user_cancel"


@router.get("/api/command/health")
def command_health():
    reachable = False
    status = None
    try:
        status = _call("GET", "/api/orchestrator/status", timeout=3)
        reachable = True
    except HTTPException:
        pass
    return {
        "ok": reachable,
        "python_uptime_seconds": int(time.time() - _STARTED),
        "orchestrator": {
            "base": ORCH_BASE,
            "reachable": reachable,
            "process_alive": bool(_PROC and _PROC.poll() is None),
            "status": status,
        },
        "adapter": "autopilot",
        "note": "using real autopilot adapter",
    }


@router.post("/api/command/submit")
def command_submit(req: CommandSubmit):
    # --- Phase A: guardrail scan ---
    if _GUARD_OK:
        try:
            _g = _guard_scan(req.command)
            if _g.get("risk") == "high":
                _log("warn", "guardrail_block", command=req.command[:100],
                     matches=[m.get("pattern") for m in _g.get("matches", [])])
                return {
                    "ok": False,
                    "error": "blocked_by_guardrails",
                    "risk": "high",
                    "matches": [m.get("pattern") for m in _g.get("matches", [])]
                }
        except Exception:
            pass
    # --- end guardrail scan ---
    body = req.model_dump(exclude_none=True)
    speak_async(f"Analyzing command: {req.command}")
    data = _call("POST", "/api/autopilot", body=body, timeout=60)
    task = data.get("task") or data
    if "task" not in data and isinstance(task, dict) and task.get("task_id"):
        data = {"ok": True, "task": task, "response": data.get("response")}

    # --- Phase 14: post-submit integration ---
    try:
        if isinstance(data, dict):
            import sys as _p14_sys
            _P14_TOOLS = r"D:\\01_PROJECTS\\AIOS\\06_TOOLS"
            if _P14_TOOLS not in _p14_sys.path:
                _p14_sys.path.insert(0, _P14_TOOLS)
            try:
                import aios_verifier as _v
                data["verification"] = _v.verify_claim("command: " + req.command, source="command")
            except Exception:
                pass
            try:
                import metacognition as _m
                data["metacognition"] = _m.calibrate(
                    str(data.get("response") or "")[:800],
                    question=req.command,
                    source="command"
                )
            except Exception:
                pass
            try:
                import social_layer as _s
                data["social"] = _s.evaluate(source="command_post", persist=False)
            except Exception:
                pass
    except Exception:
        pass
    # --- end Phase 14 ---
    _log(
        "info",
        "submit",
        command=req.command,
        task_id=(data.get("task") or {}).get("task_id") or task.get("task_id"),
        status=(data.get("task") or task).get("status"),
        risk_level=(data.get("task") or task).get("risk_level"),
        requires_confirmation=(data.get("task") or task).get("requires_confirmation"),
    )
    return data


def _update_task_file(task_id: str, status: str, note: str | None = None, decided_by: str = "boss") -> dict | None:
    """Fallback: update tasks.json directly when the shim doesn't know the task."""
    if not TASKS_FILE.exists():
        return None
    try:
        import json as _json
        data = _json.loads(TASKS_FILE.read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    tasks = data.get("tasks", [])
    updated = None
    for t in tasks:
        if t.get("task_id") == task_id:
            t["status"] = status
            t["completed_at"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
            if note:
                t["decision_note"] = note
            t["decided_by"] = decided_by
            updated = t
            break
    if updated is None:
        return None
    tmp = TASKS_FILE.with_suffix(".json.tmp")
    tmp.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    import os as _os
    _os.replace(tmp, TASKS_FILE)
    return updated

@router.post("/api/command/confirm")
def command_confirm(req: ConfirmBody):
    if req.approved:
        speak_async("Access granted. Initializing execution sequence.")
    else:
        speak_async("Access denied. Task cancelled.")

    # Try the shim first
    shim_result = None
    shim_error = None
    try:
        shim_result = _call(
            "POST",
            f"/api/tasks/{req.task_id}/confirm",
            body={
                "approved": req.approved,
                "note": req.note,
                "decided_by": req.decided_by,
            },
            timeout=60,
        )
    except HTTPException as exc:
        shim_error = str(exc.detail)

    # Always reconcile the file so pending list clears
    file_status = "APPROVED" if req.approved else "REJECTED"
    file_task = _update_task_file(req.task_id, file_status, note=req.note, decided_by=req.decided_by)

    # If both failed, error out
    if shim_result is None and file_task is None:
        _log("error", "confirm_failed", task_id=req.task_id, error=shim_error)
        raise HTTPException(404, {"ok": False, "error": {"code": "task_not_found", "message": shim_error or "Task not found."}})

    _log(
        "info" if req.approved else "warn",
        "confirm",
        task_id=req.task_id,
        approved=req.approved,
        source="shim" if shim_result else "file",
    )

    return {
        "ok": True,
        "task_id": req.task_id,
        "approved": req.approved,
        "source": "shim" if shim_result else "file",
        "task": file_task or (shim_result or {}).get("task"),
        "shim_error": shim_error,
    }


@router.post("/api/command/cancel")
def command_cancel(req: CancelBody):
    speak_async("Emergency stop received. Terminating running tasks.")
    data = _call(
        "POST",
        f"/api/tasks/{req.task_id}/cancel",
        body={"reason": req.reason},
        timeout=30,
    )
    task = data.get("task") or data
    _log("warn", "cancel", task_id=req.task_id, reason=req.reason, status=task.get("status"))
    return data


@router.get("/api/command/status")
def command_status(task_id: Optional[str] = None, limit: int = Query(25, ge=1, le=100)):
    if task_id:
        return _call("GET", f"/api/tasks/{task_id}")
    data = _call("GET", "/api/tasks")
    tasks = data.get("tasks") or []
    return {"tasks": tasks[:limit], "total": data.get("total", len(tasks))}


@router.get("/api/command/log")
def command_log(limit: int = Query(50, ge=1, le=300)):
    return {"events": _LOG[-limit:], "count": len(_LOG), "log_file": str(LOG_FILE)}
