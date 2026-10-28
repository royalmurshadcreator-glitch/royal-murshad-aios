"""
Copywriter API â€” mounts under /api/copywriter
Register in royal_server.py:
    from copywriter_api import router as copywriter_router
    app.include_router(copywriter_router)
"""
from __future__ import annotations

import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/copywriter", tags=["copywriter"])

WS = Path(r"D:\01_PROJECTS\AIOS\12_WORKSPACE")
AGENT = WS / "agents" / "copywriter"
INBOX = AGENT / "IN"
OUT = AGENT / "OUT"
FAILED = AGENT / "FAILED"
LOG = WS / "LOG" / "runs.jsonl"
PY = Path(r"D:\\01_PROJECTS\\AIOS\\18_ENV\\\.venv\\Scripts\\python\.exe")
AGENT_PY = AGENT / "agent.py"
JOBS_DB = WS / "LOG" / "jobs.jsonl"


class SubmitBody(BaseModel):
    product: str
    email: str | None = None


def _append_job(entry: dict) -> None:
    JOBS_DB.parent.mkdir(parents=True, exist_ok=True)
    with JOBS_DB.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _read_jobs(limit: int = 50) -> list[dict]:
    if not JOBS_DB.exists():
        return []
    lines = JOBS_DB.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(l) for l in lines[-limit:]]


def _read_log(limit: int = 50) -> list[dict]:
    if not LOG.exists():
        return []
    lines = LOG.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(l) for l in lines[-limit:]]


@router.post("/submit")
def submit(body: SubmitBody):
    text = body.product.strip()
    if len(text) < 20:
        raise HTTPException(400, "product description too short (min 20 chars)")
    job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    filename = f"{job_id}.txt"
    INBOX.mkdir(parents=True, exist_ok=True)
    (INBOX / filename).write_text(text, encoding="utf-8")
    entry = {
        "job_id": job_id,
        "input_file": filename,
        "email": body.email,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "queued",
    }
    _append_job(entry)
    return {"ok": True, "job_id": job_id, "status": "queued"}


@router.get("/jobs")
def jobs(limit: int = 50):
    j = _read_jobs(limit)
    log = {e.get("input"): e for e in _read_log(200)}
    for job in j:
        e = log.get(job["input_file"])
        if e and e.get("ok"):
            job["status"] = "done"
            job["output_file"] = e.get("output")
            job["duration_ms"] = e.get("ms")
        elif e:
            job["status"] = "failed"
            job["error"] = e.get("error")
        out_name = Path(job["input_file"]).stem + ".listing.txt"
        job["has_output"] = (OUT / out_name).exists()
    return {"ok": True, "count": len(j), "jobs": j}


@router.get("/jobs/{job_id}")
def job_detail(job_id: str):
    j = [x for x in _read_jobs(500) if x["job_id"] == job_id]
    if not j:
        raise HTTPException(404, "job not found")
    job = j[-1]
    out_name = Path(job["input_file"]).stem + ".listing.txt"
    out_path = OUT / out_name
    if out_path.exists():
        job["listing"] = out_path.read_text(encoding="utf-8")
        job["status"] = "done"
    elif (FAILED / job["input_file"]).exists():
        job["status"] = "failed"
    return {"ok": True, "job": job}


@router.get("/stats")
def stats():
    jobs_list = _read_jobs(500)
    log = _read_log(500)
    ok = sum(1 for e in log if e.get("ok"))
    failed = sum(1 for e in log if not e.get("ok"))
    return {
        "ok": True,
        "total_jobs": len(jobs_list),
        "completed": ok,
        "failed": failed,
        "agent": "copywriter",
        "model": "qwen2.5:3b",
    }