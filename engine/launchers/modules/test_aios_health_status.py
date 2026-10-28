"""Health contract tests use temporary SQLite databases and mocked route probes."""

import ast
import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.responses import JSONResponse

MODULES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULES_DIR.parents[2]
LAUNCHER_PATH = PROJECT_ROOT / "18_ENV" / "launchers" / "aios_backend_launcher.py"
sys.path.insert(0, str(MODULES_DIR))
import aios_health_status
from aios_health_status import build_health_report, probe_database


def load_route(name, namespace):
    tree = ast.parse(LAUNCHER_PATH.read_text(encoding="utf-8"))
    route = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
    route = copy.deepcopy(route)
    route.decorator_list = []
    module = ast.Module(body=[route], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(LAUNCHER_PATH), "exec"), namespace)
    return namespace[name]


class HealthStatusTests(unittest.TestCase):
    def test_healthy_dependencies_report_ready(self):
        report = build_health_report(True, True, 2, True)
        self.assertTrue(report["live"])
        self.assertTrue(report["ready"])
        self.assertEqual(report["status"], "ready")

    def test_unavailable_optional_asg_degrades_without_faking_failure(self):
        report = build_health_report(True, True, 2, False, asg_required=False)
        self.assertTrue(report["ready"])
        self.assertEqual(report["status"], "degraded")
        self.assertFalse(report["dependencies"]["asg_core"]["available"])
        self.assertFalse(report["dependencies"]["asg_core"]["required"])

    def test_unavailable_required_dependency_blocks_readiness_but_not_liveness(self):
        report = build_health_report(False, True, 1, True)
        self.assertTrue(report["live"])
        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "not_ready")

    def test_asg_can_be_marked_required_by_an_explicit_caller(self):
        report = build_health_report(True, True, 1, False, asg_required=True)
        self.assertFalse(report["ready"])
        self.assertTrue(report["dependencies"]["asg_core"]["required"])

    def test_zero_workforce_engines_is_visible_as_degraded(self):
        report = build_health_report(True, True, 0, True)
        self.assertTrue(report["ready"])
        self.assertEqual(report["status"], "degraded")
        self.assertEqual(report["dependencies"]["workforce"]["engine_count"], 0)

    def test_database_probe_is_read_only_and_does_not_create_missing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "test.db"
            import sqlite3
            connection = sqlite3.connect(existing)
            connection.execute("CREATE TABLE test(value INTEGER)")
            connection.close()
            self.assertTrue(probe_database(existing))
            missing = Path(temp_dir) / "missing.db"
            self.assertFalse(probe_database(missing))
            self.assertFalse(missing.exists())

    def test_health_and_readiness_route_functions_use_the_health_report(self):
        sample = build_health_report(False, True, 0, False)
        health = load_route("root_health", {"_current_health_report": lambda: sample})
        readiness = load_route(
            "root_readiness",
            {"_current_health_report": lambda: sample, "JSONResponse": JSONResponse},
        )
        self.assertFalse(health()["ready"])
        self.assertEqual(readiness().status_code, 503)

    def test_health_module_uses_mockable_probes(self):
        with patch.object(aios_health_status, "probe_database", return_value=True), patch.object(
            aios_health_status, "probe_ollama", return_value=True
        ), patch.object(aios_health_status, "probe_asg", return_value=False):
            report = aios_health_status.collect_health_report("unused", "http://ollama", 0, "http://asg")
        self.assertTrue(report["ready"])
        self.assertEqual(report["status"], "degraded")


if __name__ == "__main__":
    unittest.main()
