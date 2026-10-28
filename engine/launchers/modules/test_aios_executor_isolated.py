"""Executor behavior is tested with subprocess mocked; no host command runs."""

import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


MODULE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE_DIR))
import aios_executor


class IsolatedExecutorTests(unittest.TestCase):
    def test_blocked_command_never_reaches_host_executor(self):
        with patch.object(aios_executor.subprocess, "run") as run:
            result = aios_executor.execute("del /q important.txt")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "blocked")
        run.assert_not_called()

    def test_dry_run_never_reaches_host_executor(self):
        with patch.object(aios_executor.subprocess, "run") as run:
            result = aios_executor.execute("echo safe", dry_run=True)
        self.assertTrue(result["ok"])
        self.assertTrue(result["dry_run"])
        run.assert_not_called()

    def test_timeout_is_reported_without_running_a_real_command(self):
        with patch.object(
            aios_executor.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd="mocked", timeout=2),
        ) as run:
            result = aios_executor.execute("echo safe", timeout=2)
        self.assertEqual(result["error"], "timeout")
        run.assert_called_once()

    def test_high_risk_confirmation_gate_is_exercised_with_mocked_policy(self):
        assessment = {"safe": True, "risk": "high", "reason": "isolated test policy"}
        with patch.object(aios_executor, "check_command", return_value=assessment), patch.object(aios_executor.subprocess, "run") as run:
            denied = aios_executor.execute("mocked high-risk command")
            self.assertEqual(denied["error"], "requires_confirmation")
            run.assert_not_called()
            run.return_value = SimpleNamespace(stdout="", stderr="", returncode=0)
            approved = aios_executor.execute("mocked high-risk command", confirm_token="YES_I_AM_SURE")
        self.assertTrue(approved["ok"])
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
