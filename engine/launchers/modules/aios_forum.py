
import sqlite3
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\forum.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS threads (id INTEGER PRIMARY KEY, title TEXT, author TEXT, body TEXT)")
    return c
def create_thread(title, author, body):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO threads (title, author, body) VALUES (?,?,?)", (title, author, body))
    c.commit(); return {"ok": True, "id": cur.lastrowid}
def list_threads():
    c = _conn(); cur = c.cursor(); cur.execute("SELECT * FROM threads")
    return [{"id": r[0], "title": r[1], "author": r[2], "body": r[3]} for r in cur.fetchall()]
