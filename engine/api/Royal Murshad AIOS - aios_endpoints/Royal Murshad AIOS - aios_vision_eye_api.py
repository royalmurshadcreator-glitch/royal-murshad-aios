"""
ROYAL JARVIS - Eye Reader Control API (Phase 41)
Serves live snapshot + start/stop/status for the eye_brain_reader.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os, subprocess, sys

ROOT = Path(r"D:\\01_PROJECTS\\AIOS")
PY   = r"C:\Users\royal\AppData\Local\Programs\Python\Python312\python.exe"
SCRIPT = ROOT / "Vision" / "eye_brain_reader.py"
WORKDIR = ROOT / "Vision"
SNAPSHOT = ROOT / "Vision" / "eye_snapshot.jpg"

router = APIRouter(prefix="/api/vision/eye", tags=["vision-eye"])


def _find_pid():
    """Return PID of running eye_brain_reader.py, else None."""
    try:
        ps = (
            'Get-CimInstance Win32_Process -Filter "Name=\'python.exe\'" | '
            'Where-Object { $_.CommandLine -match \'eye_brain_reader\' } | '
            'Select-Object -First 1 -ExpandProperty ProcessId'
        )
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps],
            timeout=4, text=True, stderr=subprocess.DEVNULL
        ).strip()
        return int(out) if out else None
    except Exception:
        return None


@router.get("/snapshot")
def snapshot():
    if not SNAPSHOT.exists():
        raise HTTPException(404, "no snapshot yet â€” start the eye reader")
    return FileResponse(str(SNAPSHOT), media_type="image/jpeg",
                        headers={"Cache-Control": "no-store, max-age=0"})


@router.get("/status")
def status():
    pid = _find_pid()
    return {
        "ok": True,
        "running": pid is not None,
        "pid": pid,
        "script": str(SCRIPT),
        "snapshot_exists": SNAPSHOT.exists(),
        "snapshot_mtime": (SNAPSHOT.stat().st_mtime if SNAPSHOT.exists() else None),
    }


@router.post("/start")
def start():
    if _find_pid() is not None:
        return {"ok": True, "already_running": True}
    if not SCRIPT.exists():
        raise HTTPException(500, f"script missing: {SCRIPT}")
    try:
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NEW_CONSOLE
        subprocess.Popen(
            [PY, str(SCRIPT)],
            cwd=str(WORKDIR),
            creationflags=flags,
        )
        return {"ok": True, "started": True}
    except Exception as e:
        raise HTTPException(500, f"spawn failed: {str(e)[:200]}")


@router.post("/stop")
def stop():
    pid = _find_pid()
    if pid is None:
        return {"ok": True, "already_stopped": True}
    try:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                       timeout=5, capture_output=True)
        return {"ok": True, "stopped": True, "pid": pid}
    except Exception as e:
        raise HTTPException(500, f"kill failed: {str(e)[:200]}")


@router.get("/latest")
def latest():
    """Return the eye reader's most recent state line."""
    import json
    log = ROOT / "Vision" / "eye_state.jsonl"
    if not log.exists():
        return {"ok": False, "error": "no eye_state.jsonl"}
    try:
        with open(log, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 4096))
            tail = f.read().decode("utf-8", errors="ignore").strip().splitlines()
        if not tail:
            return {"ok": False, "error": "empty"}
        return {"ok": True, "latest": json.loads(tail[-1])}
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}