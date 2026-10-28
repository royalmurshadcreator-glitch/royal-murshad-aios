
import sqlite3
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\errors.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS errors (id INTEGER PRIMARY KEY, message TEXT, created_at TEXT)")
    return c
def log_error(message):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO errors (message, created_at) VALUES (?, datetime('now'))", (message,))
    c.commit(); return {"ok": True}
def list_errors():
    c = _conn(); cur = c.cursor(); cur.execute("SELECT * FROM errors ORDER BY id DESC LIMIT 100")
    return [{"id": r[0], "message": r[1], "created_at": r[2]} for r in cur.fetchall()]
