
import sqlite3, os, shutil
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\backups.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS backups (id INTEGER PRIMARY KEY, path TEXT, created_at TEXT)")
    return c
def create_backup(path):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO backups (path, created_at) VALUES (?, datetime('now'))", (path,))
    c.commit(); return {"ok": True, "id": cur.lastrowid}
def list_backups():
    c = _conn(); cur = c.cursor()
    cur.execute("SELECT * FROM backups")
    return [{"id": r[0], "path": r[1], "created_at": r[2]} for r in cur.fetchall()]
