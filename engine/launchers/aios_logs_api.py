"""Logs & Monitoring API."""
from fastapi import APIRouter
from pathlib import Path
from datetime import datetime
import urllib.request, json

router = APIRouter(tags=["logs"])

LOG_DIR = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\18_ENV\diagnostics")


@router.get("/api/logs/list")
def list_logs():
    if not LOG_DIR.exists():
        return {"ok": True, "logs": []}
    logs = []
    for f in sorted(LOG_DIR.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True):
        logs.append({
            "name": f.name,
            "size": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return {"ok": True, "count": len(logs), "logs": logs}


@router.get("/api/logs/errors")
def error_log(lines: int = 30):
    err = LOG_DIR / "backend_stderr.log"
    if not err.exists():
        return {"ok": True, "lines": [], "total": 0}
    try:
        with open(err, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        errors = [l for l in all_lines if any(k in l for k in ("ERROR", "FAIL", "Traceback", "Exception", "WARN"))]
        return {"ok": True, "total": len(errors), "lines": errors[-lines:]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/logs/monitoring")
def monitoring():
    result = {"ok": True, "backend_alive": False, "ollama_alive": False, "db_alive": False, "uptime_seconds": 0}
    try:
        with urllib.request.urlopen("http://127.0.0.1:9000/api/dashboard/summary", timeout=3) as r:
            d = json.loads(r.read())
            result["backend_alive"] = d.get("health", {}).get("backend", False)
            result["ollama_alive"] = d.get("health", {}).get("ollama", False)
            result["db_alive"] = d.get("health", {}).get("database", False)
            result["uptime_seconds"] = d.get("uptime_seconds", 0)
    except Exception:
        pass
    return result
