"""Client Portal - login + document access for clients."""
import uuid as _po_uuid
import json as _po_json
import sqlite3 as _po_sqlite
import hashlib as _po_hash
import secrets as _po_secrets
from datetime import datetime as _po_dt, timezone as _po_tz, timedelta as _po_td
from pathlib import Path as _po_Path

_PORTAL_DB = _DRAGON_ROOT / "config" / "portal_users.db"
_PORTAL_DB.parent.mkdir(parents=True, exist_ok=True)
_DOCSUITE_STORE = _DRAGON_ROOT / "config" / "docsuite_store.json"
_DOCS_OUT = _DRAGON_ROOT / "17_DOCS" / "generated"

def _po_now():
    return _po_dt.now(_po_tz.utc).isoformat().replace("+00:00","Z")

def _po_db():
    conn = _po_sqlite.connect(str(_PORTAL_DB))
    conn.execute("""CREATE TABLE IF NOT EXISTS portal_users (
        id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL,
        name TEXT, client_id TEXT, password_hash TEXT, salt TEXT,
        active INTEGER DEFAULT 1, created_at TEXT, last_login TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS portal_sessions (
        token TEXT PRIMARY KEY, user_id TEXT, client_id TEXT,
        created_at TEXT, expires_at TEXT)""")
    conn.commit()
    return conn

def _po_hash_pw(pw, salt):
    return _po_hash.sha256((salt + pw).encode()).hexdigest()

def _po_cleanup_sessions(conn):
    cutoff = _po_now()
    conn.execute("DELETE FROM portal_sessions WHERE expires_at < ?", (cutoff,))
    conn.commit()

def _po_find_client_by_email(email):
    if not _DOCSUITE_STORE.exists():
        return None
    try:
        d = _po_json.loads(_DOCSUITE_STORE.read_text(encoding="utf-8"))
        hist = d.get("history", [])
    except Exception:
        hist = []
    biz = _DRAGON_ROOT / "config" / "wave3_business.json"
    if biz.exists():
        try:
            b = _po_json.loads(biz.read_text(encoding="utf-8"))
            for c in b.get("clients", []):
                if (c.get("email") or "").lower() == email.lower():
                    return c
        except Exception:
            pass
    return None

@app.post("/api/portal/register")
def _portal_register(body: dict = {}):
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        return {"ok": False, "error": "email and password required"}
    if len(password) < 6:
        return {"ok": False, "error": "password min 6 chars"}
    client = _po_find_client_by_email(email)
    if not client:
        return {"ok": False, "error": "email not registered with ASG — contact support"}
    conn = _po_db()
    try:
        cur = conn.execute("SELECT id FROM portal_users WHERE email=?", (email,))
        if cur.fetchone():
            return {"ok": False, "error": "email already registered — try login"}
        salt = _po_secrets.token_hex(16)
        pw_hash = _po_hash_pw(password, salt)
        uid = _po_uuid.uuid4().hex[:12]
        conn.execute(
            "INSERT INTO portal_users (id,email,name,client_id,password_hash,salt,active,created_at) VALUES (?,?,?,?,?,?,1,?)",
            (uid, email, client.get("name"), client.get("id"), pw_hash, salt, _po_now())
        )
        conn.commit()
        return {"ok": True, "user_id": uid, "client_id": client.get("id"), "name": client.get("name")}
    finally:
        conn.close()

@app.post("/api/portal/login")
def _portal_login(body: dict = {}):
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not email or not password:
        return {"ok": False, "error": "email and password required"}
    conn = _po_db()
    _po_cleanup_sessions(conn)
    try:
        cur = conn.execute(
            "SELECT id,password_hash,salt,client_id,name,active FROM portal_users WHERE email=?",
            (email,)
        )
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": "invalid credentials"}
        uid, pw_hash, salt, client_id, name, active = row
        if not active:
            return {"ok": False, "error": "account disabled"}
        if _po_hash_pw(password, salt) != pw_hash:
            return {"ok": False, "error": "invalid credentials"}
        token = _po_secrets.token_urlsafe(32)
        expires = (_po_dt.now(_po_tz.utc) + _po_td(days=7)).isoformat().replace("+00:00","Z")
        conn.execute(
            "INSERT INTO portal_sessions (token,user_id,client_id,created_at,expires_at) VALUES (?,?,?,?,?)",
            (token, uid, client_id, _po_now(), expires)
        )
        conn.execute("UPDATE portal_users SET last_login=? WHERE id=?", (_po_now(), uid))
        conn.commit()
        return {"ok": True, "token": token, "expires_at": expires,
                "user": {"id": uid, "email": email, "name": name, "client_id": client_id}}
    finally:
        conn.close()

@app.get("/api/portal/me")
def _portal_me(token: str = ""):
    if not token:
        return {"ok": False, "error": "no token"}
    conn = _po_db()
    _po_cleanup_sessions(conn)
    try:
        cur = conn.execute(
            "SELECT user_id,client_id,expires_at FROM portal_sessions WHERE token=?",
            (token,)
        )
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": "invalid or expired session"}
        uid, client_id, expires = row
        cur = conn.execute("SELECT email,name FROM portal_users WHERE id=?", (uid,))
        urow = cur.fetchone()
        if not urow:
            return {"ok": False, "error": "user not found"}
        email, name = urow
        client = _po_find_client_by_email(email)
        return {"ok": True, "user": {"id": uid, "email": email, "name": name, "client_id": client_id},
                "client": client, "expires_at": expires}
    finally:
        conn.close()

@app.post("/api/portal/logout")
def _portal_logout(body: dict = {}):
    token = body.get("token") or ""
    if token:
        conn = _po_db()
        try:
            conn.execute("DELETE FROM portal_sessions WHERE token=?", (token,))
            conn.commit()
        finally:
            conn.close()
    return {"ok": True}

@app.get("/api/portal/documents")
def _portal_documents(token: str = ""):
    if not token:
        return {"ok": False, "error": "no token"}
    conn = _po_db()
    _po_cleanup_sessions(conn)
    try:
        cur = conn.execute("SELECT client_id FROM portal_sessions WHERE token=?", (token,))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": "invalid session"}
        client_id = row[0]
    finally:
        conn.close()

    if not _DOCSUITE_STORE.exists():
        return {"ok": True, "items": [], "total": 0}
    try:
        d = _po_json.loads(_DOCSUITE_STORE.read_text(encoding="utf-8"))
    except Exception:
        return {"ok": True, "items": [], "total": 0}

    hist = d.get("history", [])
    # Find client's name to filter
    cname = None
    biz = _DRAGON_ROOT / "config" / "wave3_business.json"
    if biz.exists():
        try:
            b = _po_json.loads(biz.read_text(encoding="utf-8"))
            for c in b.get("clients", []):
                if c.get("id") == client_id:
                    cname = c.get("name")
                    break
        except Exception:
            pass

    items = []
    for x in hist:
        if x.get("chain_client_id") == client_id:
            items.append(x)
        elif cname and x.get("client") == cname:
            items.append(x)

    result = []
    for x in items:
        f = _DOCS_OUT / x.get("file","")
        result.append({
            "id": x.get("id"),
            "type": x.get("type"),
            "doc_number": x.get("doc_number"),
            "file": x.get("file"),
            "created": x.get("created"),
            "size": f.stat().st_size if f.exists() else 0,
            "download": "/api/portal/download/" + x.get("file","") + "?token=" + token
        })
    result.sort(key=lambda x: x.get("created",""), reverse=True)
    return {"ok": True, "items": result, "total": len(result), "client_id": client_id}

@app.get("/api/portal/download/{name}")
def _portal_download(name: str, token: str = ""):
    from fastapi.responses import FileResponse as _FR
    if not token:
        return {"ok": False, "error": "no token"}
    if ".." in name or "/" in name or "\\" in name:
        return {"ok": False, "error": "invalid name"}
    conn = _po_db()
    _po_cleanup_sessions(conn)
    try:
        cur = conn.execute("SELECT client_id FROM portal_sessions WHERE token=?", (token,))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "error": "invalid session"}
        client_id = row[0]
    finally:
        conn.close()
    # Verify this doc belongs to client
    try:
        d = _po_json.loads(_DOCSUITE_STORE.read_text(encoding="utf-8"))
    except Exception:
        return {"ok": False, "error": "store unreadable"}
    hist = d.get("history", [])
    # Find client name
    cname = None
    biz = _DRAGON_ROOT / "config" / "wave3_business.json"
    if biz.exists():
        try:
            b = _po_json.loads(biz.read_text(encoding="utf-8"))
            for c in b.get("clients", []):
                if c.get("id") == client_id:
                    cname = c.get("name")
                    break
        except Exception:
            pass
    authorized = False
    for x in hist:
        if x.get("file") != name:
            continue
        if x.get("chain_client_id") == client_id or (cname and x.get("client") == cname):
            authorized = True
            break
    if not authorized:
        return {"ok": False, "error": "unauthorized"}
    f = _DOCS_OUT / name
    if not f.exists():
        return {"ok": False, "error": "file missing"}
    return _FR(str(f),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=name)

@app.get("/api/portal/users")
def _portal_users():
    """Admin: list all portal accounts."""
    conn = _po_db()
    try:
        cur = conn.execute("SELECT id,email,name,client_id,active,created_at,last_login FROM portal_users")
        rows = cur.fetchall()
        items = [{"id":r[0],"email":r[1],"name":r[2],"client_id":r[3],
                  "active":bool(r[4]),"created_at":r[5],"last_login":r[6]} for r in rows]
        return {"ok": True, "items": items, "total": len(items)}
    finally:
        conn.close()

@app.post("/api/portal/users/{uid}/reset")
def _portal_reset(uid: str, body: dict = {}):
    """Admin: reset client password."""
    new_pw = body.get("password") or _po_secrets.token_urlsafe(8)
    conn = _po_db()
    try:
        cur = conn.execute("SELECT id FROM portal_users WHERE id=?", (uid,))
        if not cur.fetchone():
            return {"ok": False, "error": "user not found"}
        salt = _po_secrets.token_hex(16)
        pw_hash = _po_hash_pw(new_pw, salt)
        conn.execute("UPDATE portal_users SET password_hash=?,salt=? WHERE id=?", (pw_hash, salt, uid))
        conn.execute("DELETE FROM portal_sessions WHERE user_id=?", (uid,))
        conn.commit()
        return {"ok": True, "new_password": new_pw}
    finally:
        conn.close()

@app.delete("/api/portal/users/{uid}")
def _portal_delete(uid: str):
    conn = _po_db()
    try:
        conn.execute("DELETE FROM portal_users WHERE id=?", (uid,))
        conn.execute("DELETE FROM portal_sessions WHERE user_id=?", (uid,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()

print("[portal] loaded")