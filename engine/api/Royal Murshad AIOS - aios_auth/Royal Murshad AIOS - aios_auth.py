"""
ROYAL JARVIS - Local Auth (Phase 40)
Multi-user login. Stdlib-only: pbkdf2_hmac + secrets for tokens.
Tables: auth_users and auth_sessions in this product's royal_auth.sqlite3.
"""
import hashlib, hmac, os, re, secrets, sqlite3, time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEM_DB = ROOT / "Royal Murshad AIOS - 04_MEMORY" / "Royal Murshad AIOS - aios_memory" / "Royal Murshad AIOS - data" / "royal_auth.sqlite3"

PBKDF2_ITERATIONS = 600_000
PBKDF2_ALGO = "sha256"
SESSION_TTL_SEC = 8 * 60 * 60
COOKIE_NAME = "royal_session"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conn():
    MEM_DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(MEM_DB), timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def ensure_schema():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS auth_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT,
                display_name TEXT,
                pw_hash TEXT NOT NULL,
                pw_salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT
            )
        """)
        session_table = c.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='auth_sessions'"
        ).fetchone()
        if not session_table:
            c.execute("""
                CREATE TABLE auth_sessions (
                    token_hash TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    ip TEXT,
                    user_agent TEXT
                )
            """)
        else:
            columns = {row[1] for row in c.execute("PRAGMA table_info(auth_sessions)")}
            if "token_hash" not in columns:
                expected = {"token", "username", "created_at", "expires_at", "ip", "user_agent"}
                if not expected.issubset(columns):
                    raise RuntimeError("Unsupported auth_sessions schema; refusing unsafe migration")
                # Rebuild transactionally so legacy raw tokens are never copied into the new table.
                c.execute("PRAGMA secure_delete=ON")
                c.execute("BEGIN IMMEDIATE")
                c.execute("""
                    CREATE TABLE auth_sessions_digest_migration (
                        token_hash TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        ip TEXT,
                        user_agent TEXT
                    )
                """)
                legacy_rows = c.execute(
                    "SELECT token,username,created_at,expires_at,ip,user_agent FROM auth_sessions"
                ).fetchall()
                for legacy in legacy_rows:
                    if not isinstance(legacy[0], str) or not legacy[0]:
                        raise RuntimeError("Invalid legacy auth session; refusing unsafe migration")
                    c.execute(
                        "INSERT INTO auth_sessions_digest_migration "
                        "(token_hash,username,created_at,expires_at,ip,user_agent) VALUES (?,?,?,?,?,?)",
                        (_token_digest(legacy[0]), *legacy[1:]),
                    )
                c.execute("DROP TABLE auth_sessions")
                c.execute("ALTER TABLE auth_sessions_digest_migration RENAME TO auth_sessions")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sess_user ON auth_sessions(username)")
        c.commit()




def _hash(password: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac(PBKDF2_ALGO, password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return dk.hex()


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _verify(password: str, salt: str, expected_hash: str) -> bool:
    calc = _hash(password, salt)
    return hmac.compare_digest(calc, expected_hash)


def _public(user_row) -> dict:
    return {
        "id": user_row["id"],
        "username": user_row["username"],
        "email": user_row["email"],
        "display_name": user_row["display_name"] or user_row["username"],
        "role": user_row["role"],
        "active": bool(user_row["active"]),
        "created_at": user_row["created_at"],
        "last_login": user_row["last_login"],
    }


def _valid_username(username):
    return isinstance(username, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,63}", username) is not None


def _valid_password(password):
    return isinstance(password, str) and 16 <= len(password) and len(password.encode("utf-8")) <= 1024


def provision_first_admin(username: str, password: str) -> dict:
    """Explicitly create the first local administrator; never runs implicitly."""
    if not _valid_username(username):
        return {"ok": False, "error": "invalid_username"}
    if not _valid_password(password):
        return {"ok": False, "error": "password_policy"}
    ensure_schema()
    salt = secrets.token_hex(16)
    encoded = _hash(password, salt)
    with _conn() as c:
        c.execute("BEGIN IMMEDIATE")
        if c.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]:
            c.rollback()
            return {"ok": False, "error": "administrator_already_provisioned"}
        c.execute("INSERT INTO auth_users (username,display_name,pw_hash,pw_salt,role,active,created_at) VALUES (?,?,?,?,?,?,?)", (username, username, encoded, salt, "admin", 1, _now_iso()))
        c.commit()
    return {"ok": True, "username": username}


def recover_local_admin(username: str, new_password: str) -> dict:
    """Reset an active local admin from the interactive local recovery tool."""
    if not _valid_username(username) or not _valid_password(new_password):
        return {"ok": False, "error": "invalid_user_or_password"}
    ensure_schema()
    salt = secrets.token_hex(16)
    encoded = _hash(new_password, salt)
    with _conn() as c:
        c.execute("BEGIN IMMEDIATE")
        user = c.execute(
            "SELECT username FROM auth_users WHERE username=? AND role='admin' AND active=1",
            (username,),
        ).fetchone()
        if not user:
            c.rollback()
            return {"ok": False, "error": "active_admin_not_found"}
        c.execute(
            "UPDATE auth_users SET pw_hash=?,pw_salt=? WHERE username=?",
            (encoded, salt, username),
        )
        c.execute("DELETE FROM auth_sessions WHERE username=?", (username,))
        c.commit()
    return {"ok": True, "sessions_invalidated": True}


def login(username: str, password: str, ip: str = None, user_agent: str = None) -> dict:
    if (
        not _valid_username(username)
        or not isinstance(password, str)
        or not password
        or len(password.encode("utf-8")) > 1024
    ):
        return {"ok": False, "error": "invalid_credentials"}
    ensure_schema()
    with _conn() as c:
        row = c.execute("SELECT * FROM auth_users WHERE username=?", (username,)).fetchone()
        if not row or not row["active"]:
            return {"ok": False, "error": "invalid_credentials"}
        if not _verify(password, row["pw_salt"], row["pw_hash"]):
            return {"ok": False, "error": "invalid_credentials"}
        token = secrets.token_urlsafe(32)
        expires = datetime.fromtimestamp(time.time() + SESSION_TTL_SEC, tz=timezone.utc).isoformat()
        c.execute(
            "INSERT INTO auth_sessions (token_hash,username,created_at,expires_at,ip,user_agent) VALUES (?,?,?,?,?,?)",
            (_token_digest(token), username, _now_iso(), expires, ip, (user_agent or "")[:200]),
        )
        c.execute("UPDATE auth_users SET last_login=? WHERE username=?", (_now_iso(), username))
        c.commit()
        return {"ok": True, "token": token, "expires_at": expires, "user": _public(row)}


def logout(token: str) -> dict:
    ensure_schema()
    if not isinstance(token, str) or not token:
        return {"ok": True}
    with _conn() as c:
        c.execute("DELETE FROM auth_sessions WHERE token_hash=?", (_token_digest(token),))
        c.commit()
    return {"ok": True}


def whoami(token: str) -> dict:
    ensure_schema()
    if not isinstance(token, str) or not token:
        return {"ok": False, "error": "no_token"}
    with _conn() as c:
        token_hash = _token_digest(token)
        s = c.execute("SELECT * FROM auth_sessions WHERE token_hash=?", (token_hash,)).fetchone()
        if not s:
            return {"ok": False, "error": "invalid_token"}
        if datetime.fromisoformat(s["expires_at"]) < datetime.now(timezone.utc):
            c.execute("DELETE FROM auth_sessions WHERE token_hash=?", (token_hash,))
            c.commit()
            return {"ok": False, "error": "expired"}
        u = c.execute("SELECT * FROM auth_users WHERE username=?", (s["username"],)).fetchone()
        if not u or not u["active"]:
            return {"ok": False, "error": "user_inactive"}
        return {"ok": True, "user": _public(u), "expires_at": s["expires_at"]}


def list_users() -> list:
    ensure_schema()
    with _conn() as c:
        rows = c.execute("SELECT * FROM auth_users ORDER BY id ASC").fetchall()
    return [_public(r) for r in rows]


def create_user(username: str, password: str, display_name=None, email=None, role="user") -> dict:
    ensure_schema()
    if not username or len(username) < 3:
        return {"ok": False, "error": "username_too_short"}
    if not password or len(password) < 3:
        return {"ok": False, "error": "password_too_short"}
    salt = secrets.token_hex(16)
    pw_hash = _hash(password, salt)
    try:
        with _conn() as c:
            c.execute(
                "INSERT INTO auth_users (username,email,display_name,pw_hash,pw_salt,role,active,created_at) "
                "VALUES (?,?,?,?,?,?,1,?)",
                (username, email, display_name or username, pw_hash, salt, role, _now_iso()),
            )
            c.commit()
        return {"ok": True, "username": username}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": "username_exists"}


def delete_user(username: str) -> dict:
    ensure_schema()
    if username == "royal":
        return {"ok": False, "error": "cannot_delete_primary_admin"}
    with _conn() as c:
        c.execute("DELETE FROM auth_sessions WHERE username=?", (username,))
        r = c.execute("DELETE FROM auth_users WHERE username=?", (username,))
        c.commit()
    return {"ok": True, "deleted": r.rowcount}


def set_password(username: str, new_password: str) -> dict:
    ensure_schema()
    if not _valid_username(username) or not _valid_password(new_password):
        return {"ok": False, "error": "password_policy"}
    salt = secrets.token_hex(16)
    pw_hash = _hash(new_password, salt)
    with _conn() as c:
        r = c.execute("UPDATE auth_users SET pw_hash=?, pw_salt=? WHERE username=?", (pw_hash, salt, username))
        c.execute("DELETE FROM auth_sessions WHERE username=?", (username,))
        c.commit()
    return {"ok": True, "updated": r.rowcount}


if __name__ == "__main__":
    raise SystemExit("Use bootstrap_local_admin.py for explicit local provisioning")
