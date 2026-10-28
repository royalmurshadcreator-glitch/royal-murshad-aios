
import sqlite3
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\photos.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS photos (id INTEGER PRIMARY KEY, filename TEXT, path TEXT)")
    return c
def upload_photo(filename, path):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO photos (filename, path) VALUES (?,?)", (filename, path))
    c.commit(); return {"ok": True, "id": cur.lastrowid}
def list_photos():
    c = _conn(); cur = c.cursor(); cur.execute("SELECT * FROM photos")
    return [{"id": r[0], "filename": r[1], "path": r[2]} for r in cur.fetchall()]
