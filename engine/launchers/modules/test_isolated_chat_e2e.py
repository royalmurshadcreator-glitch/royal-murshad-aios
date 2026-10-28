"""Isolated chat-route integration; real inference writes only to a temp SQLite DB."""

import ast
import copy
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SERVER_PATH = PROJECT_ROOT / "Royal Murshad AIOS - SERVERS" / "Royal Murshad AIOS - master" / "Royal Murshad AIOS - aios_server.py"
MEMORY_ROOT = PROJECT_ROOT / "Royal Murshad AIOS - 04_MEMORY" / "Royal Murshad AIOS - aios_memory"
DATABASE_SOURCE = MEMORY_ROOT / "Royal Murshad AIOS - aios_chat_db.py"
ENGINE_SOURCE = MEMORY_ROOT / "Royal Murshad AIOS - aios_chat_engine.py"


def _load_isolated_database(temp_root):
    tree = ast.parse(DATABASE_SOURCE.read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "ROOT" in targets or "DATA_DIR" in targets:
            node.value = ast.Call(func=ast.Name(id="Path", ctx=ast.Load()), args=[ast.Constant(str(temp_root))], keywords=[])
    module = types.ModuleType("aios_chat_db")
    module.__file__ = str(DATABASE_SOURCE)
    exec(compile(ast.fix_missing_locations(tree), str(DATABASE_SOURCE), "exec"), module.__dict__)
    return module


def _load_engine(database_module):
    sys.modules["aios_chat_db"] = database_module
    spec = importlib.util.spec_from_file_location("aios_chat_engine_isolated", ENGINE_SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.chat_db = database_module
    return module


_SERVER_TREE = None


def _load_chat_route(namespace):
    global _SERVER_TREE
    if _SERVER_TREE is None:
        _SERVER_TREE = ast.parse(SERVER_PATH.read_text(encoding="utf-8-sig"))
    tree = _SERVER_TREE
    route = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "chat_send"
    )
    route = copy.deepcopy(route)
    route.decorator_list = []
    module = ast.Module(body=[route], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(SERVER_PATH), "exec"), namespace)
    return namespace["chat_send"]


def _chat_side_effect_mocks():
    guardrails = types.ModuleType("aios_guardrails")
    guardrails.scan_input = lambda _text: {"risk": "low", "matches": []}
    verifier = types.ModuleType("aios_verifier")
    verifier.verify_response = lambda *_args, **_kwargs: {"ok": True}
    metacognition = types.ModuleType("metacognition")
    metacognition.calibrate = lambda *_args, **_kwargs: {"ok": True}
    social = types.ModuleType("social_layer")
    social.check_tone = lambda *_args, **_kwargs: {"ok": True}
    return {
        "aios_guardrails": guardrails,
        "aios_verifier": verifier,
        "metacognition": metacognition,
        "social_layer": social,
    }


class IsolatedChatRouteTests(unittest.TestCase):
    def test_route_rejects_empty_message_without_invoking_engine(self):
        engine = types.SimpleNamespace(send=lambda *_args, **_kwargs: self.fail("engine must not run"))
        route = _load_chat_route({"_CHAT_AVAILABLE": True, "_chat_engine": engine})
        self.assertEqual(route({"message": ""}), {"ok": False, "error": "empty message"})

    def test_route_reports_unavailable_chat_module(self):
        route = _load_chat_route({"_CHAT_AVAILABLE": False})
        self.assertEqual(route({"message": "hello"}), {"ok": False, "reason": "chat not loaded"})

    def test_real_local_inference_and_conversation_persist_in_isolated_database(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = _load_isolated_database(Path(temp_dir) / "memory")
            engine = _load_engine(database)
            if not engine.ollama_alive(timeout=1.0):
                self.skipTest("local Ollama service is unavailable")
            conversation = database.new_conversation(title="isolated integration test")
            route = _load_chat_route({
                "_CHAT_AVAILABLE": True,
                "_chat_db": database,
                "_chat_engine": engine,
            })
            with patch.dict(sys.modules, _chat_side_effect_mocks()):
                result = route({
                    "conversation_id": conversation["id"],
                    "message": "Reply with exactly the word READY.",
                    "model": "qwen2.5:3b",
                })

            self.assertTrue(result["ok"], result.get("error", "chat failed"))
            self.assertEqual(result["conversation_id"], conversation["id"])
            self.assertTrue(result["assistant_message"]["content"].strip())
            self.assertEqual(result["model"], "qwen2.5:3b")

            database._conn.close()
            database._conn = None
            history = database.get_messages(conversation["id"])
            self.assertEqual([item["role"] for item in history["messages"]], ["user", "assistant"])
            self.assertTrue(history["messages"][1]["content"].strip())
            database._conn.close()
            database._conn = None


if __name__ == "__main__":
    unittest.main()
