"""Dashboard summary endpoint for Royal Murshad AIOS."""
from fastapi import APIRouter
import sqlite3
import json
import os
import subprocess
from datetime import datetime

router = APIRouter(tags=["dashboard"])

@router.get("/api/dashboard/summary")
def dashboard_summary():
    result = {
        "timestamp": datetime.now().isoformat(),
        "apps": 60,
        "agents": 0,
        "records": 0,
        "tasks": {"queued": 0, "running": 0, "awaiting_approval": 0,
                  "succeeded": 0, "failed": 0, "cancelled": 0, "timed_out": 0},
        "chat": {"conversations": 0, "messages": 0},
        "models": {"count": 0, "list": []},
        "success_rate": 0.0,
        "uptime_seconds": 0,
        "agents_by_status": {"operational": 0, "activated": 0, "registered": 0},
        "health": {"backend": True, "ollama": False, "database": False}
    }

    # Apps — read registry directly, no ambiguity
    result["apps"] = 60  # honest fallback if registry read fails
    try:
        with open(r"D:\01_PROJECTS\AIOS\11_DATA\aios_app_registry.json", encoding="utf-8-sig") as _rf:
            _rd = json.load(_rf)
        if isinstance(_rd.get("apps"), list):
            result["apps"] = len(_rd["apps"])
        elif isinstance(_rd, list):
            result["apps"] = len(_rd)
    except Exception:
        pass
    except Exception:
        pass

    # Agents from registry
    try:
        with open(r"D:\01_PROJECTS\AIOS\11_DATA\aios_agent_registry.json", encoding="utf-8-sig") as f:
            reg = json.load(f)
        result["agents"] = reg.get("total_agents", 0)
        for emp in reg.get("employees", []):
            st = emp.get("status", "registered")
            if st in result["agents_by_status"]:
                result["agents_by_status"][st] += 1
    except Exception:
        pass

    # Tasks
    try:
        r = sqlite3.connect(r"D:\01_PROJECTS\AIOS\11_DATA\aios_apps.db")
        for st in result["tasks"]:
            try:
                result["tasks"][st] = r.execute("SELECT COUNT(*) FROM aios_tasks WHERE status=?", (st,)).fetchone()[0]
            except Exception:
                pass
        r.close()
    except Exception:
        pass

    # Chat
    try:
        r = sqlite3.connect(r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - 04_MEMORY\Royal Murshad AIOS - aios_memory\Royal Murshad AIOS - data\Royal Murshad AIOS - chat.db")
        result["chat"]["conversations"] = r.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        result["chat"]["messages"] = r.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        result["health"]["database"] = True
        r.close()
    except Exception:
        pass

    # Total records
    total = 0
    db_paths = [
        r"D:\01_PROJECTS\AIOS\11_DATA\aios_apps.db",
        r"D:\01_PROJECTS\AIOS\04_MEMORY\aios_memory\royal_memory.db",
        r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - 04_MEMORY\Royal Murshad AIOS - aios_memory\Royal Murshad AIOS - data\Royal Murshad AIOS - chat.db"
    ]
    for db_path in db_paths:
        try:
            r = sqlite3.connect(db_path)
            tables = r.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            for (t,) in tables:
                try:
                    total += r.execute('SELECT COUNT(*) FROM "' + t + '"').fetchone()[0]
                except Exception:
                    pass
            r.close()
        except Exception:
            pass
    result["records"] = total

    # Success rate
    succ = result["tasks"]["succeeded"]
    fail = result["tasks"]["failed"]
    denom = succ + fail
    if denom > 0:
        result["success_rate"] = round(succ / denom * 100, 1)

    # Models
    try:
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        lines = [line for line in out.stdout.split("\n")[1:] if line.strip()]
        result["models"]["count"] = len(lines)
        for line in lines:
            parts = line.split()
            if parts:
                result["models"]["list"].append(parts[0])
        result["health"]["ollama"] = True
    except Exception:
        pass

    # Uptime
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "cmdline", "create_time"]):
            cmdline = proc.info.get("cmdline") or []
            if "aios_backend_launcher" in " ".join(cmdline):
                result["uptime_seconds"] = int(datetime.now().timestamp() - proc.info["create_time"])
                break
    except Exception:
        pass


    # Extended real AIOS data
    result["data_breakdown"] = {
        "apps_registered": result["apps"],
        "agents_registered": result["agents"],
        "task_records": sum(result["tasks"].values()),
        "chat_records": result["chat"]["conversations"] + result["chat"]["messages"],
        "memory_records": 0,
        "knowledge_records": 0,
        "system_events": 0,
        "business_records": 0,
    }

    # Memory subsystem (aios_memory.db)
    try:
        r = sqlite3.connect(r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - 04_MEMORY\Royal Murshad AIOS - aios_memory\Royal Murshad AIOS - aios_memory.db")
        total_mem = 0
        for (t,) in r.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            try: total_mem += r.execute('SELECT COUNT(*) FROM "' + t + '"').fetchone()[0]
            except: pass
        r.close()
        result["data_breakdown"]["memory_records"] = total_mem
        result["records"] += total_mem
    except: pass

    # Knowledge base
    try:
        r = sqlite3.connect(r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_knowledge\Royal Murshad AIOS - knowledge.db")
        total_k = 0
        for (t,) in r.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            try: total_k += r.execute('SELECT COUNT(*) FROM "' + t + '"').fetchone()[0]
            except: pass
        r.close()
        result["data_breakdown"]["knowledge_records"] = total_k
        result["records"] += total_k
    except: pass

    # Watchtower system events (monitoring)
    try:
        r = sqlite3.connect(r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - DATA\Royal Murshad AIOS - watchtower.db")
        total_w = 0
        for (t,) in r.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            try: total_w += r.execute('SELECT COUNT(*) FROM "' + t + '"').fetchone()[0]
            except: pass
        r.close()
        result["data_breakdown"]["system_events"] = total_w
        result["records"] += total_w
    except: pass

    # Business records (informational only — NOT added to total, already counted in aios_apps.db)
    try:
        r = sqlite3.connect(r"D:\01_PROJECTS\AIOS\11_DATA\aios_apps.db")
        biz = 0
        for tbl in ["aios_users", "aios_roles", "aios_sessions", "crm_contact_records", "crm_interaction_history", "crm_company_records"]:
            try: biz += r.execute("SELECT COUNT(*) FROM " + tbl).fetchone()[0]
            except: pass
        r.close()
        result["data_breakdown"]["business_records"] = biz
        # NOTE: business_records is a SUBSET of aios_apps.db which is already in result["records"]
        # So we do NOT add it again here
    except: pass

    # Divisions count (robust — no os.path dependency)
    result["divisions"] = 0
    try:
        import json as _jd
        _div_candidates = [
            r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - DIVISIONS\_unified_registry.json",
            r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - DIVISIONS\Royal Murshad AIOS - _registry.json",
            r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - DIVISIONS\_registry.json",
        ]
        for _div_file in _div_candidates:
            try:
                with open(_div_file, encoding="utf-8-sig") as _df:
                    _dd = _jd.load(_df)
                    _n = len(_dd.get("divisions", []))
                    if _n > 0:
                        result["divisions"] = _n
                        break
            except (FileNotFoundError, OSError):
                continue
    except Exception:
        pass

    # Extended data counts (inventions, subscribers, knowledge, watchtower)
    result["inventions"] = 0
    try:
        _c = sqlite3.connect(r"D:\01_PROJECTS\AIOS\04_MEMORY\aios_memory\royal_memory.db")
        result["inventions"] = _c.execute("SELECT COUNT(*) FROM inventions").fetchone()[0]
        _c.close()
    except Exception:
        pass
    result["subscribers"] = 0
    try:
        _c = sqlite3.connect(r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_esim\Royal Murshad AIOS - aios_esim_smdpp\Royal Murshad AIOS - backend\Royal Murshad AIOS - subscribers.db")
        result["subscribers"] = _c.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
        _c.close()
    except Exception:
        pass
    result["knowledge_chunks"] = 0
    try:
        _c = sqlite3.connect(r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_knowledge\Royal Murshad AIOS - knowledge.db")
        result["knowledge_chunks"] = _c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        _c.close()
    except Exception:
        pass
    result["watchtower_records"] = 0
    try:
        _c = sqlite3.connect(r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - DATA\Royal Murshad AIOS - watchtower.db")
        _f = _c.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        _d = _c.execute("SELECT COUNT(*) FROM folders").fetchone()[0]
        result["watchtower_records"] = _f + _d
        _c.close()
    except Exception:
        pass
    result["business"] = {}
    try:
        _c = sqlite3.connect(r"D:\01_PROJECTS\AIOS\04_MEMORY\aios_memory\royal_memory.db")
        for _t in ["leads", "autopilot_events", "angel_targets", "manager_plan", "manager_decisions"]:
            try:
                result["business"][_t] = _c.execute('SELECT COUNT(*) FROM "' + _t + '"').fetchone()[0]
            except Exception:
                result["business"][_t] = 0
        _c.close()
    except Exception:
        pass

    return {"ok": True, **result}



