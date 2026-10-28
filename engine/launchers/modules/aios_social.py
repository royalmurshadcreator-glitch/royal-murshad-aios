
import sqlite3
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\social.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, platform TEXT, content TEXT)")
    return c
def create_post(platform, content):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO posts (platform, content) VALUES (?,?)", (platform, content))
    c.commit(); return {"ok": True, "id": cur.lastrowid}
def list_posts():
    c = _conn(); cur = c.cursor(); cur.execute("SELECT * FROM posts")
    return [{"id": r[0], "platform": r[1], "content": r[2]} for r in cur.fetchall()]
