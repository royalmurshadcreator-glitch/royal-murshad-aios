
import sqlite3
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\news.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS articles (id INTEGER PRIMARY KEY, title TEXT, url TEXT, source TEXT)")
    return c
def add_article(title, url, source):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO articles (title, url, source) VALUES (?,?,?)", (title, url, source))
    c.commit(); return {"ok": True, "id": cur.lastrowid}
def list_articles():
    c = _conn(); cur = c.cursor(); cur.execute("SELECT * FROM articles")
    return [{"id": r[0], "title": r[1], "url": r[2], "source": r[3]} for r in cur.fetchall()]
