
import sqlite3
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\stomach.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS meals (id INTEGER PRIMARY KEY, food TEXT, calories INTEGER)")
    return c
def log_meal(food, calories):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO meals (food, calories) VALUES (?,?)", (food, calories))
    c.commit(); return {"ok": True, "id": cur.lastrowid}
def list_meals():
    c = _conn(); cur = c.cursor(); cur.execute("SELECT * FROM meals")
    return [{"id": r[0], "food": r[1], "calories": r[2]} for r in cur.fetchall()]
