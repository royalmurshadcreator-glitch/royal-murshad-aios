"""Exercise the real launcher route functions without importing its side effects."""

import ast
import asyncio
import copy
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import HTMLResponse

MODULES_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULES_DIR.parents[2]
LAUNCHER_PATH = PROJECT_ROOT / "18_ENV" / "launchers" / "aios_backend_launcher.py"
sys.path.insert(0, str(MODULES_DIR))
from aios_dashboard_security import resolve_dashboard_html


def load_route_function(name, namespace):
    tree = ast.parse(LAUNCHER_PATH.read_text(encoding="utf-8"))
    route = next(
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name
    )
    route = copy.deepcopy(route)
    route.decorator_list = []
    module = ast.Module(body=[route], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(LAUNCHER_PATH), "exec"), namespace)
    return namespace[name]


class LauncherRouteSecurityTests(unittest.TestCase):
    def test_database_paths_are_overridable_only_by_explicit_process_config(self):
        tree = ast.parse(LAUNCHER_PATH.read_text(encoding="utf-8"))
        helper = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_storage_path"
        )
        namespace = {"_pathlib": __import__("types").SimpleNamespace(Path=Path)}
        module = ast.Module(body=[helper], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), str(LAUNCHER_PATH), "exec"), namespace)
        fallback = Path("D:/isolated/default.db")
        self.assertEqual(namespace["_storage_path"]({}, "DB_PATH", fallback), fallback)
        configured = Path("D:/isolated/override.db")
        self.assertEqual(
            namespace["_storage_path"]({"DB_PATH": str(configured)}, "DB_PATH", fallback),
            configured,
        )
        constants = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        self.assertIn("AIOS_AUTH_DB_PATH", constants)
        self.assertIn("AIOS_CHAT_DB_PATH", constants)

    def test_agent_daemon_requires_explicit_opt_in(self):
        tree = ast.parse(LAUNCHER_PATH.read_text(encoding="utf-8"))
        helper = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_agent_daemon_opted_in"
        )
        namespace = {"os": __import__("types").SimpleNamespace(environ={})}
        module = ast.Module(body=[helper], type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), str(LAUNCHER_PATH), "exec"), namespace)
        self.assertFalse(namespace["_agent_daemon_opted_in"]())
        namespace["os"].environ["AIOS_ENABLE_AGENT_DAEMON"] = "true"
        self.assertFalse(namespace["_agent_daemon_opted_in"]())
        namespace["os"].environ["AIOS_ENABLE_AGENT_DAEMON"] = "1"
        self.assertTrue(namespace["_agent_daemon_opted_in"]())

        spawn_guards = [
            node for node in tree.body
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Call)
            and isinstance(node.test.func, ast.Name)
            and node.test.func.id == "_agent_daemon_opted_in"
            and any(isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                    and child.func.attr == "Popen" for child in ast.walk(node))
        ]
        self.assertEqual(len(spawn_guards), 1)

    def test_chat_database_default_root_is_this_project(self):
        chat_db_source = PROJECT_ROOT / "Royal Murshad AIOS - 04_MEMORY" / "Royal Murshad AIOS - aios_memory" / "Royal Murshad AIOS - aios_chat_db.py"
        tree = ast.parse(chat_db_source.read_text(encoding="utf-8-sig"))
        root_assignment = next(
            node for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "ROOT" for target in node.targets)
        )
        self.assertIn("__file__", ast.unparse(root_assignment.value))
        self.assertNotIn("01_PROJECTS\\\\AIOS", ast.dump(root_assignment.value))

    def test_app_save_route_uses_temp_storage_and_rejects_bad_slug_before_writes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "app_data"
            save = load_route_function("save_app_record", {"APP_SAVE_DATA_DIR": data_dir})

            with self.assertRaises(HTTPException) as rejected:
                asyncio.run(save("../outside", {"value": "must not write"}))
            self.assertEqual(rejected.exception.status_code, 400)
            self.assertFalse(data_dir.exists())

            result = asyncio.run(save("royal-finance", {"value": "test only"}))
            self.assertTrue(result["ok"])
            saved = __import__("json").loads((data_dir / "royal-finance.json").read_text(encoding="utf-8"))
            self.assertEqual(saved[0]["value"], "test only")

    def test_dashboard_route_serves_contained_html_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "public"
            root.mkdir()
            (root / "index.html").write_text("<html><head></head><body>safe</body></html>", encoding="utf-8")
            outside = Path(temp_dir) / "outside.html"
            outside.write_text("outside", encoding="utf-8")
            view = load_route_function(
                "view_dashboard",
                {
                    "DASHBOARD_ROOT": root,
                    "resolve_dashboard_html": resolve_dashboard_html,
                    "HTTPException": HTTPException,
                    "HTMLResponse": HTMLResponse,
                },
            )

            response = asyncio.run(view(""))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"safe", response.body)
            self.assertIn(b"/dashboard-public/", response.body)
            for requested in ("../outside.html", str(outside)):
                with self.subTest(requested=requested):
                    with self.assertRaises(HTTPException) as rejected:
                        asyncio.run(view(requested))
                    self.assertEqual(rejected.exception.status_code, 400)

    def test_launcher_registers_one_dashboard_route_and_one_restricted_asset_mount(self):
        tree = ast.parse(LAUNCHER_PATH.read_text(encoding="utf-8"))
        dashboard_routes = []
        workspace_mounts = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr == "get" and decorator.args and isinstance(decorator.args[0], ast.Constant):
                            if decorator.args[0].value == "/api/view-dashboard":
                                dashboard_routes.append(node.name)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "mount":
                if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "/static-workspace":
                    workspace_mounts.append(node)
        self.assertEqual(dashboard_routes, ["view_dashboard"])
        self.assertEqual(len(workspace_mounts), 1)
        self.assertTrue(any(isinstance(child, ast.Name) and child.id == "PUBLIC_UI_ROOT" for child in ast.walk(workspace_mounts[0])))


if __name__ == "__main__":
    unittest.main()
