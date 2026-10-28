"""Extended Data API — exposes real data from all secondary DBs."""
from fastapi import APIRouter, HTTPException
import sqlite3
from pathlib import Path

router = APIRouter(tags=["extended-data"])

ROYAL_MEMORY = r"D:\01_PROJECTS\AIOS\04_MEMORY\aios_memory\royal_memory.db"
KNOWLEDGE_DB = r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_knowledge\Royal Murshad AIOS - knowledge.db"
SUBSCRIBERS_DB = r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - TOOLS\Royal Murshad AIOS - aios_esim\Royal Murshad AIOS - aios_esim_smdpp\Royal Murshad AIOS - backend\Royal Murshad AIOS - subscribers.db"
WATCHTOWER_DB = r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - DATA\Royal Murshad AIOS - watchtower.db"


def _q(db, sql, params=None):
    try:
        c = sqlite3.connect(db)
        c.row_factory = sqlite3.Row
        rows = [dict(r) for r in c.execute(sql, params or []).fetchall()]
        c.close()
        return rows
    except Exception:
        return []


# === INVENTIONS ===
@router.get("/api/inventions/list")
def inventions_list():
    rows = _q(ROYAL_MEMORY, "SELECT * FROM inventions ORDER BY created_at DESC LIMIT 100")
    return {"ok": True, "count": len(rows), "inventions": rows}

@router.get("/api/inventions/stats")
def inventions_stats():
    try:
        c = sqlite3.connect(ROYAL_MEMORY)
        n = c.execute("SELECT COUNT(*) FROM inventions").fetchone()[0]
        n_agents = c.execute("SELECT COUNT(*) FROM invention_agents").fetchone()[0]
        c.close()
        return {"ok": True, "inventions": n, "invention_agents": n_agents}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# === SUBSCRIBERS ===
@router.get("/api/subscribers/list")
def subscribers_list():
    rows = _q(SUBSCRIBERS_DB, "SELECT * FROM subscribers LIMIT 100")
    return {"ok": True, "count": len(rows), "subscribers": rows}

@router.get("/api/subscribers/plans")
def subscribers_plans():
    rows = _q(SUBSCRIBERS_DB, "SELECT * FROM plans LIMIT 100")
    return {"ok": True, "count": len(rows), "plans": rows}

@router.get("/api/subscribers/orders")
def subscribers_orders():
    rows = _q(SUBSCRIBERS_DB, "SELECT * FROM orders LIMIT 100")
    return {"ok": True, "count": len(rows), "orders": rows}

@router.get("/api/subscribers/stats")
def subscribers_stats():
    try:
        c = sqlite3.connect(SUBSCRIBERS_DB)
        subs = c.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
        plans = c.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
        orders = c.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        c.close()
        return {"ok": True, "subscribers": subs, "plans": plans, "orders": orders}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# === KNOWLEDGE ===
@router.get("/api/knowledge/stats")
def knowledge_stats():
    try:
        c = sqlite3.connect(KNOWLEDGE_DB)
        chunks = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        sources = c.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        c.close()
        return {"ok": True, "chunks": chunks, "sources": sources}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/api/knowledge/sources")
def knowledge_sources():
    rows = _q(KNOWLEDGE_DB, "SELECT * FROM sources LIMIT 100")
    return {"ok": True, "count": len(rows), "sources": rows}

@router.get("/api/knowledge/search")
def knowledge_search(q: str = "", limit: int = 10):
    if not q:
        return {"ok": True, "query": "", "count": 0, "chunks": []}
    rows = _q(KNOWLEDGE_DB, "SELECT * FROM chunks WHERE text LIKE ? LIMIT ?", (f"%{q}%", limit))
    return {"ok": True, "query": q, "count": len(rows), "chunks": rows}


# === WATCHTOWER ===
@router.get("/api/watchtower/stats")
def watchtower_stats():
    try:
        c = sqlite3.connect(WATCHTOWER_DB)
        files = c.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        folders = c.execute("SELECT COUNT(*) FROM folders").fetchone()[0]
        scans = c.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        drives = c.execute("SELECT COUNT(*) FROM drives").fetchone()[0]
        c.close()
        return {"ok": True, "files": files, "folders": folders, "scans": scans, "drives": drives,
                "total_records": files + folders + scans + drives}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/api/watchtower/files")
def watchtower_files(limit: int = 100):
    rows = _q(WATCHTOWER_DB, "SELECT * FROM files LIMIT ?", (limit,))
    return {"ok": True, "count": len(rows), "files": rows}


# === BUSINESS DATA ===
@router.get("/api/business/leads")
def business_leads():
    rows = _q(ROYAL_MEMORY, "SELECT * FROM leads LIMIT 100")
    return {"ok": True, "count": len(rows), "leads": rows}

@router.get("/api/business/autopilot")
def business_autopilot(limit: int = 50):
    rows = _q(ROYAL_MEMORY, "SELECT * FROM autopilot_events ORDER BY rowid DESC LIMIT ?", (limit,))
    return {"ok": True, "count": len(rows), "events": rows}

@router.get("/api/business/manager_plan")
def business_manager_plan():
    rows = _q(ROYAL_MEMORY, "SELECT * FROM manager_plan ORDER BY rowid DESC LIMIT 20")
    return {"ok": True, "count": len(rows), "plans": rows}

@router.get("/api/business/angel_targets")
def business_angel_targets():
    rows = _q(ROYAL_MEMORY, "SELECT * FROM angel_targets LIMIT 50")
    return {"ok": True, "count": len(rows), "targets": rows}

@router.get("/api/business/stats")
def business_stats():
    try:
        c = sqlite3.connect(ROYAL_MEMORY)
        result = {}
        for tbl in ["leads", "autopilot_events", "angel_targets", "daily_targets", "manager_plan",
                    "manager_decisions", "novelty_checks", "inventions", "invention_agents",
                    "agent_state", "agent_activity", "work_queue", "pacing_events", "pacing_state"]:
            try:
                result[tbl] = c.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()[0]
            except Exception:
                result[tbl] = 0
        c.close()
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}
