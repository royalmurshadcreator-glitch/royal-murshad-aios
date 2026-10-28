"""Royal Jarvis AIOS Storage Box backend.

Local library only; this module does not start a network server.
Secrets use AES-256-GCM with a random data key wrapped by Windows DPAPI.
Do not expose this module directly as a public API.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SCHEMA_VERSION = 1
SECRET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$")
SECTION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
FORBIDDEN_CONFIG_KEY = re.compile(
    r"(secret|password|passwd|token|api.?key|credential|private.?key|"
    r"passphrase|authorization|cookie|session.?key)",
    re.IGNORECASE,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class StorageBox:
    """Versioned configuration and encrypted-secret storage for local AIOS use."""

    def __init__(self, root: str | Path | None = None):
        configured = os.environ.get("ROYAL_STORAGE_BOX_DIR")
        self.root = Path(root or configured or
                         r"D:\01_PROJECTS\AIOS\08_DATA\royal_storage_box")
        self.db_path = self.root / "storage_box.sqlite3"
        self.key_path = self.root / "master.key.dpapi"

    def _require_initialized(self) -> None:
        if not self.db_path.is_file() or not self.key_path.is_file():
            raise RuntimeError("storage_box_not_initialized")

    @staticmethod
    def _dpapi():
        if os.name != "nt":
            raise RuntimeError("windows_dpapi_required")
        try:
            import win32crypt
            return win32crypt
        except ImportError as exc:
            raise RuntimeError("pywin32_win32crypt_required") from exc

    def _load_data_key(self, create: bool = False) -> bytes:
        dpapi = self._dpapi()

        if self.key_path.is_file():
            protected = self.key_path.read_bytes()
            result = dpapi.CryptUnprotectData(protected, None, None, None, 1)
            key = result[1]
            if len(key) != 32:
                raise RuntimeError("invalid_storage_box_key_length")
            return key

        if not create:
            raise RuntimeError("storage_box_key_missing")

        self.root.mkdir(parents=True, exist_ok=True)
        key = os.urandom(32)
        protected = dpapi.CryptProtectData(
            key, "Royal Jarvis AIOS Storage Box key",
            None, None, None, 1
        )

        # Exclusive temporary file plus atomic replacement.
        temp = self.key_path.with_suffix(".dpapi.tmp")
        with open(temp, "xb") as handle:
            handle.write(protected)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, self.key_path)

        # Validate DPAPI round-trip before the key is used.
        result = dpapi.CryptUnprotectData(
            self.key_path.read_bytes(), None, None, None, 1
        )
        if result[1] != key:
            raise RuntimeError("storage_box_key_validation_failed")
        return key

    @contextmanager
    def _db(self):
        self._require_initialized()
        connection = sqlite3.connect(
            str(self.db_path), timeout=10, isolation_level="DEFERRED"
        )
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA synchronous=FULL")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> dict:
        """Create the schema and DPAPI-wrapped data key; safe to repeat."""
        self.root.mkdir(parents=True, exist_ok=True)
        self._load_data_key(create=True)

        with self._db_initializing() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS storage_meta (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    schema_version INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS secrets (
                    secret_id TEXT PRIMARY KEY,
                    label TEXT NOT NULL,
                    category TEXT NOT NULL,
                    ciphertext BLOB NOT NULL,
                    last4 TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS config_current (
                    section TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    config_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    actor TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS config_history (
                    section TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    config_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    note TEXT NOT NULL,
                    PRIMARY KEY (section, version)
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    detail_json TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL
                );
            """)
            db.execute(
                "INSERT OR IGNORE INTO storage_meta(id,schema_version,created_at) VALUES(1,?,?)",
                (SCHEMA_VERSION, _now())
            )
            row = db.execute(
                "SELECT schema_version FROM storage_meta WHERE id=1"
            ).fetchone()
            if not row or row["schema_version"] != SCHEMA_VERSION:
                raise RuntimeError("unsupported_storage_box_schema")
        return self.health()

    @contextmanager
    def _db_initializing(self):
        """Initialization-only connection; no schema assumptions."""
        connection = sqlite3.connect(str(self.db_path), timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _audit(self, db, actor: str, action: str, target: str,
               outcome: str = "ok", detail: dict | None = None) -> None:
        prev = db.execute(
            "SELECT event_hash FROM audit_events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        prev_hash = prev["event_hash"] if prev else ""
        payload = {
            "created_at": _now(),
            "actor": (actor or "system")[:100],
            "action": action[:100],
            "target": target[:160],
            "outcome": outcome[:40],
            "detail_json": _canonical(detail or {}),
        }
        event_hash = hashlib.sha256(
            (prev_hash + "\n" + _canonical(payload)).encode("utf-8")
        ).hexdigest()
        db.execute("""
            INSERT INTO audit_events(
                event_id,created_at,actor,action,target,outcome,
                detail_json,prev_hash,event_hash
            ) VALUES(?,?,?,?,?,?,?,?,?)
        """, (
            uuid.uuid4().hex, payload["created_at"], payload["actor"],
            payload["action"], payload["target"], payload["outcome"],
            payload["detail_json"], prev_hash, event_hash
        ))

    def save_secret(self, secret_id: str, label: str, value: str,
                    category: str = "general", actor: str = "owner") -> dict:
        if not SECRET_ID_RE.fullmatch(secret_id or ""):
            raise ValueError("invalid_secret_id")
        if not isinstance(value, str) or not value:
            raise ValueError("empty_secret_value")
        if len(value.encode("utf-8")) > 65536:
            raise ValueError("secret_value_too_large")

        key = self._load_data_key()
        nonce = os.urandom(12)
        encrypted = nonce + AESGCM(key).encrypt(
            nonce, value.encode("utf-8"),
            f"royal-storage-box|{secret_id}|1".encode("utf-8")
        )
        now = _now()
        label = (label or secret_id).strip()[:160]
        category = (category or "general").strip()[:80]
        last4 = value[-4:]

        with self._db() as db:
            old = db.execute(
                "SELECT created_at,version FROM secrets WHERE secret_id=?",
                (secret_id,)
            ).fetchone()
            version = (old["version"] + 1) if old else 1
            created_at = old["created_at"] if old else now
            db.execute("""
                INSERT INTO secrets(
                    secret_id,label,category,ciphertext,last4,version,
                    created_at,updated_at,enabled
                ) VALUES(?,?,?,?,?,?,?,?,1)
                ON CONFLICT(secret_id) DO UPDATE SET
                    label=excluded.label, category=excluded.category,
                    ciphertext=excluded.ciphertext, last4=excluded.last4,
                    version=excluded.version, updated_at=excluded.updated_at,
                    enabled=1
            """, (
                secret_id, label, category, encrypted, last4,
                version, created_at, now
            ))
            self._audit(db, actor, "secret.save", secret_id,
                        detail={"version": version, "category": category})
        return {"ok": True, "secret_id": secret_id, "label": label,
                "category": category, "version": version, "masked": "••••" + last4}

    def list_secrets(self) -> dict:
        """Metadata only: never returns raw secret values or ciphertext."""
        with self._db() as db:
            rows = db.execute("""
                SELECT secret_id,label,category,last4,version,created_at,
                       updated_at,enabled FROM secrets ORDER BY secret_id
            """).fetchall()
        return {
            "ok": True,
            "count": len(rows),
            "items": [{
                "secret_id": r["secret_id"], "label": r["label"],
                "category": r["category"], "masked": "••••" + r["last4"],
                "version": r["version"], "created_at": r["created_at"],
                "updated_at": r["updated_at"], "enabled": bool(r["enabled"])
            } for r in rows]
        }

    def get_secret(self, secret_id: str, actor: str = "backend") -> str:
        """Backend-only retrieval; a future HTTP handler must never return this value."""
        key = self._load_data_key()
        with self._db() as db:
            row = db.execute(
                "SELECT ciphertext,enabled FROM secrets WHERE secret_id=?",
                (secret_id,)
            ).fetchone()
            if not row or not row["enabled"]:
                raise KeyError("secret_not_found_or_disabled")
            blob = row["ciphertext"]
            if len(blob) < 29:
                raise RuntimeError("invalid_secret_ciphertext")
            plaintext = AESGCM(key).decrypt(
                blob[:12], blob[12:],
                f"royal-storage-box|{secret_id}|1".encode("utf-8")
            ).decode("utf-8")
            self._audit(db, actor, "secret.read", secret_id)
            return plaintext

    def delete_secret(self, secret_id: str, actor: str = "owner") -> dict:
        with self._db() as db:
            row = db.execute(
                "SELECT version FROM secrets WHERE secret_id=?", (secret_id,)
            ).fetchone()
            if not row:
                return {"ok": False, "error": "not_found"}
            db.execute("DELETE FROM secrets WHERE secret_id=?", (secret_id,))
            self._audit(db, actor, "secret.delete", secret_id,
                        detail={"previous_version": row["version"]})
        return {"ok": True, "secret_id": secret_id, "deleted": True}

    @staticmethod
    def _validate_config(section: str, config: dict) -> str:
        if not SECTION_RE.fullmatch(section or ""):
            raise ValueError("invalid_config_section")
        if not isinstance(config, dict):
            raise ValueError("config_must_be_an_object")

        def walk(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if FORBIDDEN_CONFIG_KEY.search(str(key)):
                        raise ValueError("secret_like_config_key_not_allowed:" + str(key))
                    walk(value)
            elif isinstance(obj, list):
                for value in obj:
                    walk(value)

        walk(config)
        encoded = json.dumps(config, ensure_ascii=False, allow_nan=False)
        if len(encoded.encode("utf-8")) > 131072:
            raise ValueError("config_too_large")
        return encoded

    def save_config_section(self, section: str, config: dict,
                            actor: str = "owner", note: str = "update") -> dict:
        encoded = self._validate_config(section, config)
        with self._db() as db:
            old = db.execute(
                "SELECT version FROM config_current WHERE section=?", (section,)
            ).fetchone()
            version = (old["version"] + 1) if old else 1
            now = _now()
            actor = (actor or "owner")[:100]
            db.execute("""
                INSERT INTO config_current(section,version,config_json,updated_at,actor)
                VALUES(?,?,?,?,?)
                ON CONFLICT(section) DO UPDATE SET version=excluded.version,
                    config_json=excluded.config_json,updated_at=excluded.updated_at,
                    actor=excluded.actor
            """, (section, version, encoded, now, actor))
            db.execute("""
                INSERT INTO config_history(
                    section,version,config_json,created_at,actor,note
                ) VALUES(?,?,?,?,?,?)
            """, (section, version, encoded, now, actor, (note or "update")[:300]))
            self._audit(db, actor, "config.save", section,
                        detail={"version": version, "note": (note or "")[:120]})
        return {"ok": True, "section": section, "version": version, "updated_at": now}

    def get_config_section(self, section: str) -> dict:
        with self._db() as db:
            row = db.execute(
                "SELECT version,config_json,updated_at,actor FROM config_current WHERE section=?",
                (section,)
            ).fetchone()
        if not row:
            return {"ok": True, "section": section, "version": 0, "config": {}}
        return {"ok": True, "section": section, "version": row["version"],
                "config": json.loads(row["config_json"]),
                "updated_at": row["updated_at"], "actor": row["actor"]}

    def list_config_history(self, section: str) -> dict:
        with self._db() as db:
            rows = db.execute("""
                SELECT version,created_at,actor,note FROM config_history
                WHERE section=? ORDER BY version DESC
            """, (section,)).fetchall()
        return {"ok": True, "section": section,
                "items": [dict(r) for r in rows]}

    def restore_config_section(self, section: str, version: int,
                               actor: str = "owner") -> dict:
        with self._db() as db:
            row = db.execute("""
                SELECT config_json FROM config_history
                WHERE section=? AND version=?
            """, (section, version)).fetchone()
        if not row:
            return {"ok": False, "error": "version_not_found"}
        config = json.loads(row["config_json"])
        # Restoring creates a new version; history is never rewritten.
        result = self.save_config_section(
            section, config, actor=actor, note=f"rollback to version {version}"
        )
        result["restored_from_version"] = version
        return result

    def verify_audit_chain(self) -> dict:
        expected_prev = ""
        count = 0
        with self._db() as db:
            rows = db.execute("SELECT * FROM audit_events ORDER BY seq").fetchall()
            for r in rows:
                payload = {
                    "created_at": r["created_at"], "actor": r["actor"],
                    "action": r["action"], "target": r["target"],
                    "outcome": r["outcome"], "detail_json": r["detail_json"]
                }
                calculated = hashlib.sha256(
                    (expected_prev + "\n" + _canonical(payload)).encode("utf-8")
                ).hexdigest()
                if r["prev_hash"] != expected_prev or r["event_hash"] != calculated:
                    return {"ok": True, "valid": False, "events_checked": count,
                            "bad_sequence": r["seq"]}
                expected_prev = r["event_hash"]
                count += 1
        return {"ok": True, "valid": True, "events_checked": count}

    def audit_events(self, limit: int = 100) -> dict:
        limit = max(1, min(int(limit), 500))
        with self._db() as db:
            rows = db.execute("""
                SELECT seq,event_id,created_at,actor,action,target,outcome,
                       detail_json,prev_hash,event_hash
                FROM audit_events ORDER BY seq DESC LIMIT ?
            """, (limit,)).fetchall()
        items = []
        for r in rows:
            item = dict(r)
            item["detail"] = json.loads(item.pop("detail_json"))
            items.append(item)
        return {"ok": True, "items": items}

    def health(self) -> dict:
        if not self.db_path.is_file() or not self.key_path.is_file():
            return {"ok": False, "initialized": False, "schema_version": SCHEMA_VERSION}
        key_ok = len(self._load_data_key()) == 32
        with self._db() as db:
            meta = db.execute("SELECT schema_version FROM storage_meta WHERE id=1").fetchone()
            secrets_count = db.execute("SELECT COUNT(*) AS n FROM secrets").fetchone()["n"]
            configs_count = db.execute("SELECT COUNT(*) AS n FROM config_current").fetchone()["n"]
            audit_count = db.execute("SELECT COUNT(*) AS n FROM audit_events").fetchone()["n"]
        return {
            "ok": bool(key_ok and meta and meta["schema_version"] == SCHEMA_VERSION),
            "initialized": True, "schema_version": meta["schema_version"] if meta else None,
            "encryption": "AES-256-GCM", "key_protection": "Windows DPAPI current user",
            "secrets_count": secrets_count, "config_sections": configs_count,
            "audit_events": audit_count
        }