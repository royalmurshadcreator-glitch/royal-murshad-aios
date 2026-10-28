
import sqlite3
from pathlib import Path
DB = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\data\contacts.db")
def _conn():
    DB.parent.mkdir(exist_ok=True, parents=True)
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, name TEXT, email TEXT, phone TEXT)")
    return c
def add_contact(name, email, phone):
    c = _conn(); cur = c.cursor()
    cur.execute("INSERT INTO contacts (name, email, phone) VALUES (?,?,?)", (name, email, phone))
    c.commit(); return {"ok": True, "id": cur.lastrowid}
def list_contacts():
    c = _conn(); cur = c.cursor(); cur.execute("SELECT * FROM contacts")
    return [{"id": r[0], "name": r[1], "email": r[2], "phone": r[3]} for r in cur.fetchall()]
