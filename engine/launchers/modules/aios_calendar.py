
import sqlite3
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\calendar.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, title TEXT, date TEXT, time TEXT, description TEXT)")
    return c
def create_event(title, date, time, description=""):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO events (title, date, time, description) VALUES (?,?,?,?)", (title, date, time, description))
    c.commit(); return {"ok": True, "id": cur.lastrowid}
def list_events():
    c = _conn(); cur = c.cursor(); cur.execute("SELECT * FROM events")
    return [{"id": r[0], "title": r[1], "date": r[2], "time": r[3], "description": r[4]} for r in cur.fetchall()]
