"""
Generalized agent API ??? serves /api/agent/{name}/*
Works for any agent that has workspace/agents/{name}/config.json
Also keeps /api/copywriter/* alive as an alias.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/agent", tags=["agent"])
alias_router = APIRouter(prefix="/api/copywriter", tags=["copywriter-alias"])

WS       = Path(r"D:\01_PROJECTS\AIOS\12_WORKSPACE")
AGENTS   = WS / "agents"
LOG      = WS / "LOG" / "runs.jsonl"
JOBS_DB  = WS / "LOG" / "jobs.jsonl"


class SubmitBody(BaseModel):
    text: str = ""
    product: str = ""   # backwards compat with old copywriter panel
    email: str | None = None


def _agent_dir(name: str) -> Path:
    d = AGENTS / name
    if not d.is_dir() or not (d / "config.json").exists():
        raise HTTPException(404, f"agent not found: {name}")
    return d


def _agent_config(name: str) -> dict:
    return json.loads((_agent_dir(name) / "config.json").read_text(encoding="utf-8"))


def _append_job(entry: dict) -> None:
    JOBS_DB.parent.mkdir(parents=True, exist_ok=True)
    with JOBS_DB.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _read_jobs(agent: str | None = None, limit: int = 100) -> list[dict]:
    if not JOBS_DB.exists():
        return []
    out = []
    for line in JOBS_DB.read_text(encoding="utf-8").strip().splitlines():
        try:
            e = json.loads(line)
            if agent is None or e.get("agent") == agent:
                out.append(e)
        except Exception:
            pass
    return out[-limit:]


def _read_log(limit: int = 500) -> list[dict]:
    if not LOG.exists():
        return []
    out = []
    for line in LOG.read_text(encoding="utf-8").strip().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out[-limit:]


def _do_submit(name: str, text: str, email: str | None):
    cfg = _agent_config(name)
    if len(text) < 20:
        raise HTTPException(400, "input too short (min 20 chars)")
    job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    filename = f"{job_id}.txt"
    inbox = _agent_dir(name) / "IN"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / filename).write_text(text, encoding="utf-8")
    entry = {
        "job_id": job_id,
        "agent": name,
        "input_file": filename,
        "email": email,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "queued",
    }
    _append_job(entry)
    return {"ok": True, "job_id": job_id, "agent": name, "status": "queued"}


def _do_jobs(name: str, limit: int = 100):
    jobs = _read_jobs(agent=name, limit=limit)
    log_map = {e.get("input"): e for e in _read_log(500) if e.get("agent") == name}
    out_dir = _agent_dir(name) / "OUT"
    failed_dir = _agent_dir(name) / "FAILED"
    for job in jobs:
        e = log_map.get(job.get("input_file"))
        if e and e.get("ok"):
            job["status"] = "done"
            job["output_file"] = e.get("output")
            job["duration_ms"] = e.get("ms")
        elif e:
            job["status"] = "failed"
            job["error"] = e.get("error")
        cfg = _agent_config(name)
        stem = Path(job.get("input_file") or "").stem
        out_name = stem + cfg.get("output_extension", ".out")
        job["has_output"] = (out_dir / out_name).exists()
    return {"ok": True, "agent": name, "count": len(jobs), "jobs": jobs}


def _do_job_detail(name: str, job_id: str):
    jobs = [j for j in _read_jobs(agent=name, limit=500) if j["job_id"] == job_id]
    if not jobs:
        raise HTTPException(404, "job not found")
    job = jobs[-1]
    cfg = _agent_config(name)
    stem = Path(job.get("input_file") or "").stem
    out_name = stem + cfg.get("output_extension", ".out")
    out_path = _agent_dir(name) / "OUT" / out_name
    if out_path.exists():
        job["output"] = out_path.read_text(encoding="utf-8")
        job["status"] = "done"
    elif (_agent_dir(name) / "FAILED" / job["input_file"]).exists():
        job["status"] = "failed"
    return {"ok": True, "job": job}


def _do_stats(name: str):
    jobs = _read_jobs(agent=name, limit=500)
    log = [e for e in _read_log(500) if e.get("agent") == name]
    ok = sum(1 for e in log if e.get("ok"))
    failed = sum(1 for e in log if not e.get("ok"))
    cfg = _agent_config(name)
    return {
        "ok": True,
        "agent": name,
        "description": cfg.get("description", ""),
        "model": cfg.get("model", ""),
        "total_jobs": len(jobs),
        "completed": ok,
        "failed": failed,
    }


# --- Generic routes ---
@router.post("/{name}/submit")
def submit(name: str, body: SubmitBody):
    text = (body.text or body.product or "").strip()
    return _do_submit(name, text, body.email)

@router.get("/{name}/jobs")
def jobs(name: str, limit: int = 100):
    return _do_jobs(name, limit)

@router.get("/{name}/jobs/{job_id}")
def job_detail(name: str, job_id: str):
    return _do_job_detail(name, job_id)

@router.get("/{name}/stats")
def stats(name: str):
    return _do_stats(name)

@router.get("/")
def list_agents():
    if not AGENTS.exists():
        return {"ok": True, "agents": []}
    agents = []
    for d in sorted(AGENTS.iterdir()):
        if d.is_dir() and (d / "config.json").exists():
            try:
                cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
                agents.append({
                    "name": d.name,
                    "description": cfg.get("description", ""),
                    "model": cfg.get("model", ""),
                })
            except Exception:
                pass
    return {"ok": True, "count": len(agents), "agents": agents}


# --- Copywriter backwards-compat routes ---
@alias_router.post("/submit")
def cw_submit(body: SubmitBody):
    text = (body.product or body.text or "").strip()
    return _do_submit("copywriter", text, body.email)

@alias_router.get("/jobs")
def cw_jobs(limit: int = 100):
    return _do_jobs("copywriter", limit)

@alias_router.get("/jobs/{job_id}")
def cw_job_detail(job_id: str):
    return _do_job_detail("copywriter", job_id)

@alias_router.get("/stats")
def cw_stats():
    return _do_stats("copywriter")

# ============================================================================
# Job API (added 2026-09-14)
# Submit a job to an agent, get a job_id back, poll for result.
# ============================================================================

from fastapi import APIRouter as _FastAPIRouter
from fastapi.responses import PlainTextResponse as _PlainTextResponse
import uuid as _uuid
import json as _json

_job_router = _FastAPIRouter(tags=["agent-jobs"])

_AGENT_ROOT = Path(r"D:\01_PROJECTS\AIOS\12_WORKSPACE\agents")
_AGENT_JOB_LOG = Path(r"D:\01_PROJECTS\AIOS\12_WORKSPACE\LOG\jobs.jsonl")


class JobSubmitBody(BaseModel):
    content: str
    filename_hint: str | None = None


def _agent_dir(name: str) -> Path:
    d = _AGENT_ROOT / name
    if not d.exists():
        raise HTTPException(404, f"agent not found: {name}")
    return d


def _write_job_log(entry: dict) -> None:
    try:
        _AGENT_JOB_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _AGENT_JOB_LOG.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(entry) + "\n")
    except Exception:
        pass


@_job_router.post("/api/agent/{name}/job")
def submit_agent_job(name: str, body: JobSubmitBody):
    """
    Submit content to an agent. Returns job_id immediately.
    The agent's runner will pick up the file and process it within ~5 seconds.
    """
    d = _agent_dir(name)
    inbox = d / "IN"
    inbox.mkdir(parents=True, exist_ok=True)

    job_id = _uuid.uuid4().hex[:16]
    ext = ".txt"
    if body.filename_hint and "." in body.filename_hint:
        ext = "." + body.filename_hint.rsplit(".", 1)[1]
    fname = f"job_{job_id}{ext}"
    (inbox / fname).write_text(body.content, encoding="utf-8")

    _write_job_log({
        "ts": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "job_id": job_id,
        "agent": name,
        "action": "submitted",
        "bytes": len(body.content),
    })

    return {
        "ok": True,
        "job_id": job_id,
        "agent": name,
        "filename": fname,
        "message": "Job queued. Poll /api/agent/{name}/job/{id} for result.",
    }


@_job_router.get("/api/agent/{name}/job/{job_id}")
def get_agent_job(name: str, job_id: str):
    """
    Check a job's status.
    - pending: still in IN/ or being processed
    - done:    output ready in OUT/
    - failed:  moved to FAILED/
    """
    d = _agent_dir(name)

    # Check IN/ first (still queued)
    for f in (d / "IN").glob(f"job_{job_id}*"):
        return {"ok": True, "job_id": job_id, "agent": name, "status": "pending", "filename": f.name}

    # Check FAILED/
    for f in (d / "FAILED").glob(f"job_{job_id}*"):
        return {"ok": False, "job_id": job_id, "agent": name, "status": "failed", "error": "see FAILED/ folder"}

    # Check OUT/ (success) ? filename stem matches job_<id>
    for f in (d / "OUT").glob(f"job_{job_id}*"):
        content = f.read_text(encoding="utf-8", errors="replace")
        return {
            "ok": True,
            "job_id": job_id,
            "agent": name,
            "status": "done",
            "output_filename": f.name,
            "output_bytes": f.stat().st_size,
            "content": content,
        }

    return {"ok": False, "job_id": job_id, "agent": name, "status": "unknown", "error": "job_id not found"}


def register_job_routes(app):
    """Call this from royal_server.py after other routers are mounted."""
    app.include_router(_job_router)