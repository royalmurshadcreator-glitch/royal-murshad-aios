
import sqlite3
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\slides.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS slides (id INTEGER PRIMARY KEY, title TEXT, content TEXT)")
    return c
def create_slide(title, content):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO slides (title, content) VALUES (?,?)", (title, content))
    c.commit(); return {"ok": True, "id": cur.lastrowid}
def list_slides():
    c = _conn(); cur = c.cursor(); cur.execute("SELECT * FROM slides")
    return [{"id": r[0], "title": r[1], "content": r[2]} for r in cur.fetchall()]
