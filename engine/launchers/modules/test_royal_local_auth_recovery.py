"""Local admin password recovery is tested only against a temporary DB."""

import importlib.util
import secrets
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUTH_SOURCE = PROJECT_ROOT / "Royal Murshad AIOS - API" / "Royal Murshad AIOS - aios_auth" / "Royal Murshad AIOS - aios_auth.py"


def load_auth():
    spec = importlib.util.spec_from_file_location("royal_local_auth_recovery_test", AUTH_SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LocalAuthRecoveryTests(unittest.TestCase):
    def test_recovery_rotates_password_and_invalidates_sessions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            auth = load_auth()
            auth.MEM_DB = Path(temp_dir) / "auth.sqlite3"
            previous_password = secrets.token_urlsafe(24)
            replacement_password = secrets.token_urlsafe(24)
            auth.provision_first_admin("local-owner", previous_password)
            session = auth.login("local-owner", previous_password)
            result = auth.recover_local_admin("local-owner", replacement_password)
            self.assertTrue(result["ok"])
            self.assertTrue(result["sessions_invalidated"])
            self.assertFalse(auth.whoami(session["token"])["ok"])
            self.assertFalse(auth.login("local-owner", previous_password)["ok"])
            self.assertTrue(auth.login("local-owner", replacement_password)["ok"])
            with closing(sqlite3.connect(auth.MEM_DB)) as connection:
                row = connection.execute(
                    "SELECT pw_hash,pw_salt FROM auth_users WHERE username=?",
                    ("local-owner",),
                ).fetchone()
            self.assertNotIn(replacement_password.encode("utf-8"), auth.MEM_DB.read_bytes())
            self.assertTrue(auth._verify(replacement_password, row[1], row[0]))


if __name__ == "__main__":
    unittest.main()
