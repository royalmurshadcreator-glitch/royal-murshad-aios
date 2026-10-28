
import sqlite3
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\sheets.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS sheets (id INTEGER PRIMARY KEY, name TEXT, data TEXT)")
    return c
def create_sheet(name):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO sheets (name, data) VALUES (?, ?)", (name, "{}"))
    c.commit(); return {"ok": True, "id": cur.lastrowid}
def update_sheet(sheet_id, data):
    c = _conn(); cur = c.cursor()
    cur.execute("UPDATE sheets SET data = ? WHERE id = ?", (data, sheet_id))
    c.commit(); return {"ok": True}
def list_sheets():
    c = _conn(); cur = c.cursor(); cur.execute("SELECT id, name FROM sheets")
    return [{"id": r[0], "name": r[1]} for r in cur.fetchall()]
