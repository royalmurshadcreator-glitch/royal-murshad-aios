"""
ASG Audit Schema â€” Phase 1
Normalizes all source logs into one unified, hash-chained event stream.

Sources:
  1. executor_audit.jsonl       â€” Guard-executed commands
  2. orchestrator.jsonl         â€” Task lifecycle
  3. scheduler.jsonl            â€” Agent scheduler runs
  4. command_center/events.jsonl â€” Command center events
  5. feeling_events.jsonl       â€” Emotion engine
  6. gesture_log.jsonl          â€” Vision gestures

Master: D:\\\\AIOS\\03_MEMORY\\data\\audit_master.jsonl
"""
import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(r"D:\\01_PROJECTS\\AIOS")
MASTER_FILE = ROOT / "04_MEMORY" / "aios_memory" / "data" / "audit_master.jsonl"
MASTER_FILE.parent.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "executor": {
        "path": ROOT / "12_WORKSPACE" / "LOG" / "executor_audit.jsonl",
        "category": "execution",
        "label": "Executor Guard Audit",
        "actor_kind": "system",
    },
    "orchestrator": {
        "path": ROOT / "data" / "orchestrator" / "logs" / "orchestrator.jsonl",
        "category": "task",
        "label": "Orchestrator Task Lifecycle",
        "actor_kind": "system",
    },
    "scheduler": {
        "path": ROOT / "03_AGENTS" / "aios_computer_agent" / "logs" / "scheduler.jsonl",
        "category": "scheduler",
        "label": "Agent Scheduler Runs",
        "actor_kind": "agent",
    },
    "command_center": {
        "path": ROOT / "Logs" / "command_center" / "events.jsonl",
        "category": "command",
        "label": "Command Center Events",
        "actor_kind": "user",
    },
    "feeling": {
        "path": ROOT / "04_MEMORY" / "aios_memory" / "data" / "feeling_events.jsonl",
        "category": "emotion",
        "label": "Feeling Engine Events",
        "actor_kind": "system",
    },
    "gesture": {
        "path": ROOT / "Vision" / "gesture_log.jsonl",
        "category": "vision",
        "label": "Vision Gesture Events",
        "actor_kind": "user",
    },
}


# ============================================================
# HASH CHAIN
# ============================================================
def _hash_event(event: dict, prev_hash: str) -> str:
    """SHA256(prev_hash + canonical_json(event_without_hash))."""
    clone = {k: v for k, v in event.items() if k not in ("hash", "prev_hash", "id")}
    canonical = json.dumps(clone, sort_keys=True, separators=(",", ":"), default=str)
    payload = (prev_hash or "") + canonical
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _last_master_hash() -> str:
    """Return the hash of the last line in master file (or '' if empty)."""
    if not MASTER_FILE.exists():
        return ""
    try:
        with MASTER_FILE.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0:
                return ""
            # read last ~8KB, find last line
            read_size = min(8192, size)
            f.seek(size - read_size)
            data = f.read().decode("utf-8", errors="ignore")
            lines = [l for l in data.splitlines() if l.strip()]
            if not lines:
                return ""
            last = json.loads(lines[-1])
            return last.get("hash", "")
    except Exception:
        return ""


# ============================================================
# PER-SOURCE PARSERS
# ============================================================
def _parse_executor(raw: dict) -> dict:
    ts = raw.get("ts") or raw.get("timestamp") or datetime.utcnow().isoformat()
    kind = raw.get("kind") or raw.get("action") or "event"
    msg = raw.get("message") or raw.get("text") or kind
    level = (raw.get("level") or "info").lower()
    severity = "error" if level in ("error", "err", "critical") else ("warn" if level in ("warn", "warning") else "info")
    return {
        "ts": ts,
        "type": "executed",
        "category": "execution",
        "severity": severity,
        "actor": {"kind": "system", "id": "executor", "name": "Executor Guard"},
        "action": kind,
        "resource": {"type": "command", "id": msg[:80]},
        "result": "blocked" if level == "error" and "block" in msg.lower() else "ok",
        "message": msg,
    }


def _parse_orchestrator(raw: dict) -> dict:
    ts = raw.get("ts") or datetime.utcnow().isoformat()
    evt = raw.get("event") or "orchestrator.event"
    task_id = raw.get("task_id") or raw.get("taskId") or ""
    frm = raw.get("from", "")
    to = raw.get("to", "")
    msg = evt
    if task_id:
        msg = f"{evt} Â· {task_id[:24]}"
    if frm and to:
        msg += f" ({frm} â†’ {to})"
    level = (raw.get("level") or "info").lower()
    severity = "error" if level == "error" else ("warn" if level == "warn" else "info")
    return {
        "ts": ts,
        "type": evt.split(".")[-1] if "." in evt else "event",
        "category": "task",
        "severity": severity,
        "actor": {"kind": "system", "id": "orchestrator", "name": "Orchestrator"},
        "action": evt,
        "resource": {"type": "task", "id": task_id},
        "result": "ok",
        "correlation_id": task_id or None,
        "message": msg,
    }


def _parse_scheduler(raw: dict) -> dict:
    ts = raw.get("ts") or datetime.utcnow().isoformat()
    agent = raw.get("agent") or "unknown"
    action = raw.get("action") or "run"
    result = raw.get("result") or {}
    ok = result.get("ok", True)
    stdout = (result.get("stdout") or "").strip().splitlines()
    summary = stdout[0] if stdout else ""
    msg = f"{agent}: {action}"
    if summary:
        msg += f" â†’ {summary[:100]}"
    severity = "info" if ok else "error"
    return {
        "ts": ts,
        "type": "run",
        "category": "scheduler",
        "severity": severity,
        "actor": {"kind": "agent", "id": agent, "name": agent},
        "action": action,
        "resource": {"type": "agent", "id": agent},
        "result": "ok" if ok else "failed",
        "message": msg,
        "payload": {"stdout_tail": (result.get("stdout") or "")[-300:], "rc": result.get("rc")},
    }


def _parse_command_center(raw: dict) -> dict:
    ts = raw.get("ts") or datetime.utcnow().isoformat()
    evt = raw.get("event") or raw.get("type") or "command.event"
    msg = raw.get("message") or evt
    return {
        "ts": ts,
        "type": evt.split(".")[-1] if "." in evt else "event",
        "category": "command",
        "severity": (raw.get("level") or "info").lower() if (raw.get("level") or "info").lower() in ("info","warn","error") else "info",
        "actor": {"kind": "user", "id": raw.get("user") or "local", "name": "Operator"},
        "action": evt,
        "resource": {"type": "command", "id": raw.get("command_id") or ""},
        "result": raw.get("result") or "ok",
        "message": msg,
    }


def _parse_feeling(raw: dict) -> dict:
    ts = raw.get("ts") or datetime.utcnow().isoformat()
    evt = raw.get("event") or "feeling.event"
    states = raw.get("states") or {}
    top_state = max(states.items(), key=lambda kv: kv[1])[0] if states else ""
    msg = f"{evt} Â· peak={top_state}"
    severity = "warn" if evt in ("human_stressed", "caution", "risk_detected") else "info"
    return {
        "ts": ts,
        "type": "emotion",
        "category": "emotion",
        "severity": severity,
        "actor": {"kind": "system", "id": "feeling_engine", "name": "Feeling Engine"},
        "action": evt,
        "resource": {"type": "state", "id": top_state},
        "result": "ok",
        "message": msg,
        "payload": {"states": states, "effects": raw.get("effects")},
    }


def _parse_gesture(raw: dict) -> dict:
    ts = raw.get("ts") or datetime.utcnow().isoformat()
    gesture = raw.get("gesture") or "?"
    command = raw.get("command") or ""
    conf = raw.get("confidence") or raw.get("conf")
    msg = f"{gesture} â†’ {command}"
    if conf:
        try: msg += f" ({int(float(conf)*100)}%)"
        except Exception: pass
    return {
        "ts": ts,
        "type": "gesture",
        "category": "vision",
        "severity": "info",
        "actor": {"kind": "user", "id": "operator", "name": "Operator"},
        "action": gesture,
        "resource": {"type": "command", "id": command},
        "result": "ok",
        "message": msg,
    }


PARSERS = {
    "executor": _parse_executor,
    "orchestrator": _parse_orchestrator,
    "scheduler": _parse_scheduler,
    "command_center": _parse_command_center,
    "feeling": _parse_feeling,
    "gesture": _parse_gesture,
}


# ============================================================
# PUBLIC FUNCTIONS
# ============================================================
def get_sources() -> list:
    """Return metadata about each source."""
    out = []
    for key, meta in SOURCES.items():
        p = meta["path"]
        exists = p.exists()
        size = p.stat().st_size if exists else 0
        lines = 0
        if exists and size > 0:
            try:
                with p.open("rb") as f:
                    lines = sum(1 for _ in f)
            except Exception:
                lines = 0
        out.append({
            "key": key,
            "label": meta["label"],
            "category": meta["category"],
            "path": str(p),
            "exists": exists,
            "size_kb": round(size / 1024, 1),
            "line_count": lines,
        })
    return out


def get_schema() -> dict:
    """Return the canonical event schema definition."""
    return {
        "version": "1.0",
        "fields": {
            "id": "sha256-prefix unique id",
            "ts": "ISO8601 timestamp (UTC)",
            "type": "short event type (executed|run|transitioned|emotion|gesture|...)",
            "category": "execution|task|scheduler|command|emotion|vision|security",
            "severity": "info|warn|error|critical",
            "actor": {"kind": "system|agent|user", "id": "str", "name": "str"},
            "action": "verb (open_app|read_screen|task.created|...)",
            "resource": {"type": "task|app|file|command|state", "id": "str"},
            "result": "ok|failed|blocked",
            "correlation_id": "optional task/job id",
            "message": "human-readable summary",
            "source_file": "origin jsonl file key",
            "payload": "original raw event (for forensics)",
            "hash": "sha256(prev_hash + canonical_json)",
            "prev_hash": "previous event's hash",
        },
    }


def read_source(source_key: str, limit: int = 200) -> list:
    """Read one source, normalize, return latest events (no hash)."""
    if source_key not in SOURCES:
        return []
    meta = SOURCES[source_key]
    parser = PARSERS[source_key]
    p = meta["path"]
    if not p.exists():
        return []
    events = []
    try:
        with p.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line in lines[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except Exception:
                continue
            try:
                norm = parser(raw)
            except Exception:
                continue
            norm["source_file"] = source_key
            norm["payload"] = norm.get("payload", raw)
            events.append(norm)
    except Exception:
        return []
    return events


def read_all(limit: int = 200) -> list:
    """Read all sources, normalize, merge, sort by ts desc."""
    all_events = []
    for key in SOURCES.keys():
        all_events.extend(read_source(key, limit=limit))
    # sort by ts (desc)
    def ts_key(e):
        return str(e.get("ts") or "")
    all_events.sort(key=ts_key, reverse=True)
    return all_events[:limit]


def append_to_master(events: list) -> int:
    """Append normalized events to master with hash chain. Returns count added."""
    if not events:
        return 0
    prev = _last_master_hash()
    added = 0
    with MASTER_FILE.open("a", encoding="utf-8") as f:
        for e in events:
            clone = {k: v for k, v in e.items() if k not in ("hash", "prev_hash", "id")}
            h = _hash_event(clone, prev)
            clone["prev_hash"] = prev
            clone["hash"] = h
            clone["id"] = "evt_" + h[:16]
            f.write(json.dumps(clone, default=str) + "\n")
            prev = h
            added += 1
    return added


def sync_master() -> dict:
    """Read all sources â†’ append new (dedup by (ts, action, source_file)) â†’ return stats."""
    existing_keys = set()
    if MASTER_FILE.exists():
        try:
            with MASTER_FILE.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    try:
                        e = json.loads(line)
                        key = (str(e.get("ts") or ""), str(e.get("action") or ""), str(e.get("source_file") or ""), str(e.get("message") or ""))
                        existing_keys.add(key)
                    except Exception:
                        continue
        except Exception:
            pass
    new_events = []
    for key in SOURCES.keys():
        for e in read_source(key, limit=500):
            ek = (str(e.get("ts") or ""), str(e.get("action") or ""), str(e.get("source_file") or ""), str(e.get("message") or ""))
            if ek not in existing_keys:
                new_events.append(e)
                existing_keys.add(ek)
    added = append_to_master(new_events)
    total = 0
    if MASTER_FILE.exists():
        try:
            with MASTER_FILE.open("rb") as f:
                total = sum(1 for _ in f)
        except Exception:
            total = 0
    return {"added": added, "total_master": total, "master_path": str(MASTER_FILE)}


def read_master(limit: int = 100) -> list:
    """Return latest events from the master hash-chained file."""
    if not MASTER_FILE.exists():
        return []
    try:
        with MASTER_FILE.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        out = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out
    except Exception:
        return []
