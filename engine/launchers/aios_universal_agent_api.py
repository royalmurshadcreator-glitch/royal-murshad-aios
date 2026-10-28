"""Universal Agent Executor — makes all 247 registered agents operational."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import urllib.request
from pathlib import Path

router = APIRouter(tags=["agent-executor"])

REGISTRY_PATH = Path(r"D:\01_PROJECTS\AIOS\11_DATA\aios_agent_registry.json")
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
TASK_API = "http://127.0.0.1:9000/api/royal-tasks/submit"
RUN_API = "http://127.0.0.1:9000/api/royal-tasks/run"

AVAILABLE_TOOLS = {
    "ai.query":         "Ask the LLM a question. Args: {prompt, model, num_predict}",
    "audit.query":      "Query audit logs. Args: {query}",
    "storage.read":     "Read a file. Args: {path}",
    "storage.write":    "Write a file. Args: {path, content}",
    "app.crud.read":    "Read from DB table. Args: {table, limit}",
    "chat.send":        "Send chat message. Args: {conversation_id, message}",
    "vpn.device.create":"Register VPN device. Args: {name}",
}

GATED_TOOLS = {
    "storage.delete": "Delete file (requires approval)",
    "mail.send":      "Send email (requires approval)",
    "app.crud.delete":"Delete DB row (requires approval)",
    "system.shell":   "Shell command (requires approval)",
}

VALID_MODELS = {
    "qwen2.5:3b", "qwen2.5:3b-64k", "qwen2.5-coder:7b",
    "qwen2.5-coder:7b-64k", "qwen2.5-coder-64k:latest",
    "aios-brain:latest", "nomic-embed-text:latest"
}

class ExecuteBody(BaseModel):
    task: str = ""
    model: str = "qwen2.5:3b"


def _load_agents():
    try:
        with open(REGISTRY_PATH, encoding="utf-8-sig") as f:
            return json.load(f).get("employees", [])
    except Exception:
        return []


def _find_agent(agent_id: str):
    for a in _load_agents():
        if str(a.get("id")) == str(agent_id):
            return a
        if a.get("name", "").lower() == agent_id.lower():
            return a
    return None


def _call_ollama(prompt: str, model: str = "qwen2.5:3b", timeout: int = 60) -> str:
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 300, "temperature": 0.2}
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read()).get("response", "").strip()
    except Exception as e:
        return f"ERROR: {e}"


def _submit_task(tool: str, args: dict):
    body = json.dumps({"tool": tool, "args": args}).encode()
    req = urllib.request.Request(TASK_API, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _run_task(task_id: str):
    req = urllib.request.Request(f"{RUN_API}/{task_id}", data=b"", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _parse_llm_json(text: str):
    """Extract JSON object from LLM response, robust to preamble/postamble."""
    if not text:
        return None
    # Find first { and last }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        return None
    candidate = text[start:end]
    try:
        return json.loads(candidate)
    except Exception:
        # Try to clean common issues: trailing commas, single quotes
        try:
            candidate = candidate.replace(",}", "}").replace(",]", "]")
            return json.loads(candidate)
        except Exception:
            return None


@router.get("/api/agent/{agent_id}/info")
def agent_info(agent_id: str):
    a = _find_agent(agent_id)
    if not a:
        raise HTTPException(404, f"agent not found: {agent_id}")
    return {
        "ok": True,
        "agent": a,
        "tools_available": list(AVAILABLE_TOOLS.keys()),
        "tools_gated": list(GATED_TOOLS.keys()),
    }


@router.post("/api/agent/{agent_id}/execute")
def execute_agent(agent_id: str, body: ExecuteBody):
    a = _find_agent(agent_id)
    if not a:
        raise HTTPException(404, f"agent not found: {agent_id}")

    task_text = body.task.strip()
    if not task_text:
        raise HTTPException(400, "task required")

    # Sanitize model
    model = body.model if body.model in VALID_MODELS else "qwen2.5:3b"

    # Step 1: Ask LLM which tool
    tools_desc = "\n".join([f"  - {name}: {desc}" for name, desc in AVAILABLE_TOOLS.items()])
    routing_prompt = f"""You are {a.get('name')}, {a.get('role')} in the {a.get('tier')} tier, team "{a.get('team', a.get('tier'))}".
Your specialization: {a.get('job', a.get('role'))}
Your assigned module: {a.get('module', 'universal_executor')}

You MUST respond in your role's voice and expertise. If you are a Security agent, answer with security expertise. If you are a Sales agent, answer with sales expertise. Your response must reflect YOUR specific role, not a generic AI.

Task: {task_text}

Available tools (choose ONE):
{tools_desc}

RULES:
1. Choose exactly one tool from the list.
2. For questions/analysis/general tasks → use "ai.query"
3. For audit/logs → use "audit.query"  
4. For file reads → use "storage.read"
5. Never invent tool names.
6. In your "args.prompt" for ai.query, INCLUDE your role context so the model stays in character.

Respond with ONE JSON object only:
{{"tool": "ai.query", "args": {{"prompt": "{task_text}", "model": "qwen2.5:3b", "num_predict": 200}}, "reasoning": "brief explanation"}}
"""

    llm_raw = _call_ollama(routing_prompt, model=model)
    decision = _parse_llm_json(llm_raw) or {}

    tool = decision.get("tool", "")
    args = decision.get("args", {}) if isinstance(decision.get("args"), dict) else {}
    reasoning = decision.get("reasoning", "")

    # Step 2: Validate tool — fallback if invalid
    if tool not in AVAILABLE_TOOLS and tool not in GATED_TOOLS:
        # LLM picked invalid tool — fallback to ai.query
        reasoning = (reasoning + " | FALLBACK: invalid tool '" + str(tool) + "', using ai.query").strip(" |")
        tool = "ai.query"
        args = {"prompt": task_text}

    # Step 3: Normalize args per tool
    if tool == "ai.query":
        if not args.get("prompt") or len(str(args.get("prompt", "")).strip()) < 3:
            args["prompt"] = task_text
        # Inject role context so the LLM stays in character
        role_prefix = f"You are {a.get('name')}, {a.get('role')} in the {a.get('tier')} tier. "
        if not args["prompt"].startswith("You are"):
            args["prompt"] = role_prefix + args["prompt"]
        if args.get("model") not in VALID_MODELS:
            args["model"] = model
        try:
            np = int(args.get("num_predict", 200))
            args["num_predict"] = max(10, min(np, 1000))
        except (ValueError, TypeError):
            args["num_predict"] = 200
    elif tool == "audit.query":
        if not args.get("query"):
            args["query"] = task_text[:100]
    elif tool == "storage.read":
        if not args.get("path"):
            # Invalid args for storage.read — fallback to ai.query
            tool = "ai.query"
            args = {"prompt": task_text, "model": model, "num_predict": 200}
    elif tool == "storage.write":
        if not args.get("path") or not args.get("content"):
            tool = "ai.query"
            args = {"prompt": task_text, "model": model, "num_predict": 200}
    elif tool == "app.crud.read":
        if not args.get("table"):
            args["table"] = "aios_tasks"
        args["limit"] = args.get("limit", 10)

    # Step 4: Submit
    submit = _submit_task(tool, args)
    task_id = submit.get("task_id")
    status = submit.get("status")

    if not task_id:
        return {
            "ok": False,
            "agent": a.get("name"),
            "reasoning": reasoning,
            "tool": tool,
            "args": args,
            "error": submit.get("error", "task submission failed"),
            "task_id": None,
        }

    # Step 5: Gated tools → return awaiting_approval
    if status == "awaiting_approval":
        return {
            "ok": True,
            "agent": a.get("name"),
            "reasoning": reasoning,
            "tool": tool,
            "task_id": task_id,
            "status": "awaiting_approval",
            "note": "Gated tool. Requires admin approval.",
        }

    # Step 6: Run task
    _run_task(task_id)

    return {
        "ok": True,
        "agent": a.get("name"),
        "agent_id": a.get("id"),
        "reasoning": reasoning,
        "tool": tool,
        "args": args,
        "task_id": task_id,
        "status": "running",
        "poll_url": f"/api/royal-tasks/{task_id}",
    }
