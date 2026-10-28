
import sqlite3
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\knowledge_module.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS knowledge (id INTEGER PRIMARY KEY, title TEXT, content TEXT)")
    return c
def add_knowledge(title, content):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO knowledge (title, content) VALUES (?,?)", (title, content))
    c.commit(); return {"ok": True, "id": cur.lastrowid}
def search_knowledge(query):
    c = _conn(); cur = c.cursor()
    cur.execute("SELECT * FROM knowledge WHERE title LIKE ? OR content LIKE ?", (f"%{query}%", f"%{query}%"))
    return [{"id": r[0], "title": r[1], "content": r[2]} for r in cur.fetchall()]
