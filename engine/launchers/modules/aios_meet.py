
import sqlite3
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\meetings.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS meetings (id INTEGER PRIMARY KEY, title TEXT, link TEXT, time TEXT)")
    return c
def create_meeting(title, link, time):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO meetings (title, link, time) VALUES (?,?,?)", (title, link, time))
    c.commit(); return {"ok": True, "id": cur.lastrowid}
def list_meetings():
    c = _conn(); cur = c.cursor(); cur.execute("SELECT * FROM meetings")
    return [{"id": r[0], "title": r[1], "link": r[2], "time": r[3]} for r in cur.fetchall()]
