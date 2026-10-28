
"""Audit log — records actions for governance."""
import sqlite3
from pathlib import Path
from datetime import datetime

DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\audit.db")


def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY,
            action TEXT,
            actor TEXT,
            details TEXT,
            ts TEXT
        )
    """)
    return c


def record(action, actor="system", details=""):
    c = _conn()
    cur = c.cursor()
    cur.execute(
        "INSERT INTO audit_log (action, actor, details, ts) VALUES (?,?,?,?)",
        (action, actor, details, datetime.now().isoformat())
    )
    c.commit()
    rid = cur.lastrowid
    c.close()
    return {"ok": True, "id": rid}


def list_events(limit=100):
    c = _conn()
    cur = c.cursor()
    cur.execute(
        "SELECT id, action, actor, details, ts FROM audit_log ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = [{"id": r[0], "action": r[1], "actor": r[2], "details": r[3], "ts": r[4]}
            for r in cur.fetchall()]
    c.close()
    return rows


def stats():
    c = _conn()
    cur = c.cursor()
    total = cur.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    c.close()
    return {"ok": True, "total_events": total}
