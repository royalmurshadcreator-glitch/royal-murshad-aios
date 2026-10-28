"""Isolated tests for project-local auth; no live account DB is touched."""

import importlib.util
import hashlib
import secrets
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUTH_SOURCE = PROJECT_ROOT / "Royal Murshad AIOS - API" / "Royal Murshad AIOS - aios_auth" / "Royal Murshad AIOS - aios_auth.py"


def load_auth():
    spec = importlib.util.spec_from_file_location("royal_local_auth_test", AUTH_SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LocalAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.auth = load_auth()
        self.auth.MEM_DB = Path(self.temp.name) / "auth.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def test_schema_does_not_create_a_default_admin(self):
        self.auth.ensure_schema()
        with closing(sqlite3.connect(self.auth.MEM_DB)) as connection:
            count = connection.execute("SELECT COUNT(*) FROM auth_users").fetchone()[0]
        self.assertEqual(count, 0)
        self.assertFalse(self.auth.login("bootstrap", secrets.token_urlsafe(24))["ok"])

    def test_explicit_provisioning_hashes_password_and_supports_session_lifecycle(self):
        password = secrets.token_urlsafe(24)
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            created = self.auth.provision_first_admin("local-owner", password)
            duplicate = self.auth.provision_first_admin("another-owner", secrets.token_urlsafe(24))
            login = self.auth.login("local-owner", password)
        self.assertTrue(created["ok"])
        self.assertFalse(duplicate["ok"])
        self.assertTrue(login["ok"])
        identity = self.auth.whoami(login["token"])
        self.assertTrue(identity["ok"])
        self.assertEqual(identity["user"]["role"], "admin")
        with closing(sqlite3.connect(self.auth.MEM_DB)) as connection:
            session_hash = connection.execute(
                "SELECT token_hash FROM auth_sessions WHERE username=?", ("local-owner",)
            ).fetchone()[0]
            stored_hash, stored_salt = connection.execute(
                "SELECT pw_hash,pw_salt FROM auth_users WHERE username=?", ("local-owner",)
            ).fetchone()
        self.assertEqual(session_hash, hashlib.sha256(login["token"].encode("utf-8")).hexdigest())
        self.assertNotIn(login["token"].encode("utf-8"), self.auth.MEM_DB.read_bytes())
        self.assertNotEqual(stored_hash, password)
        self.assertNotIn(password.encode("utf-8"), self.auth.MEM_DB.read_bytes())
        self.assertTrue(self.auth._verify(password, stored_salt, stored_hash))
        self.assertNotIn(password, stdout.getvalue() + stderr.getvalue())
        self.assertNotIn(login["token"], stdout.getvalue() + stderr.getvalue())
        self.assertFalse(self.auth.whoami(secrets.token_urlsafe(24))["ok"])
        with closing(sqlite3.connect(self.auth.MEM_DB)) as connection:
            connection.execute(
                "UPDATE auth_sessions SET expires_at=? WHERE username=?",
                ("2000-01-01T00:00:00+00:00", "local-owner"),
            )
            connection.commit()
        self.assertEqual(self.auth.whoami(login["token"])["error"], "expired")
        self.auth.logout(login["token"])
        self.assertFalse(self.auth.whoami(login["token"])["ok"])

    def test_legacy_session_tokens_are_migrated_to_digests(self):
        legacy_token = secrets.token_urlsafe(32)
        with closing(sqlite3.connect(self.auth.MEM_DB)) as connection:
            connection.execute("""
                CREATE TABLE auth_sessions (
                    token TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    ip TEXT,
                    user_agent TEXT
                )
            """)
            connection.execute(
                "INSERT INTO auth_sessions VALUES (?,?,?,?,?,?)",
                (legacy_token, "legacy-owner", "2026-01-01T00:00:00+00:00",
                 "2099-01-01T00:00:00+00:00", "127.0.0.1", "isolated-test"),
            )
            connection.commit()

        self.auth.ensure_schema()

        with closing(sqlite3.connect(self.auth.MEM_DB)) as connection:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(auth_sessions)")}
            migrated = connection.execute(
                "SELECT token_hash,username,created_at,expires_at,ip,user_agent FROM auth_sessions"
            ).fetchone()
        self.assertNotIn("token", columns)
        self.assertIn("token_hash", columns)
        self.assertEqual(migrated[0], hashlib.sha256(legacy_token.encode("utf-8")).hexdigest())
        self.assertEqual(migrated[1:], (
            "legacy-owner", "2026-01-01T00:00:00+00:00",
            "2099-01-01T00:00:00+00:00", "127.0.0.1", "isolated-test",
        ))
        self.assertNotIn(legacy_token, tuple(str(value) for value in migrated))
        self.assertTrue(self.auth.provision_first_admin(
            "legacy-owner", secrets.token_urlsafe(24)
        )["ok"])
        self.assertTrue(self.auth.whoami(legacy_token)["ok"])
        self.auth.logout(legacy_token)
        self.assertFalse(self.auth.whoami(legacy_token)["ok"])

    def test_bootstrap_requires_strong_password_and_valid_username(self):
        self.assertFalse(self.auth.provision_first_admin("x", secrets.token_urlsafe(24))["ok"])
        self.assertFalse(self.auth.provision_first_admin("owner", (('x' * 8)))["ok"])
        self.assertFalse(self.auth.MEM_DB.exists())

    def test_login_rejects_malformed_passwords_without_creating_accounts(self):
        for password in (None, {}, "", "x" * 1025):
            with self.subTest(password_type=type(password).__name__):
                self.assertFalse(self.auth.login("local-owner", password)["ok"])
        self.assertFalse(self.auth.MEM_DB.exists())

    def test_source_has_no_implicit_bootstrap_assignment_or_function(self):
        source = AUTH_SOURCE.read_text(encoding="utf-8-sig")
        self.assertNotIn("DEFAULT_ADMIN", source)
        self.assertNotIn("_bootstrap_admin", source)
        self.assertIn("provision_first_admin", source)


if __name__ == "__main__":
    unittest.main()
