"""Read-only health probes and honest liveness/readiness reporting."""

import json
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen


def probe_database(database_path):
    if not isinstance(database_path, (str, Path)) or not database_path:
        return False
    path = Path(database_path)
    if not path.is_file():
        return False
    connection = None
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.5)
        return connection.execute("SELECT 1").fetchone() == (1,)
    except (OSError, sqlite3.Error, ValueError):
        return False
    finally:
        if connection is not None:
            connection.close()


def _read_json(url, timeout):
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status < 200 or response.status >= 300:
                return None
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def probe_ollama(ollama_url, timeout=0.75):
    if not isinstance(ollama_url, str) or not ollama_url:
        return False
    try:
        parsed = urlsplit(ollama_url)
        tags_url = f"{parsed.scheme}://{parsed.netloc}/api/tags"
        if not parsed.scheme or not parsed.netloc:
            return False
    except (AttributeError, TypeError, ValueError):
        return False
    return isinstance(_read_json(tags_url, timeout), dict)


def probe_asg(asg_base_url, timeout=0.5):
    if not asg_base_url:
        return False
    result = _read_json(asg_base_url.rstrip("/") + "/api/asg/health", timeout)
    return isinstance(result, dict) and result.get("ok") is True


def build_health_report(database_ok, ollama_ok, workforce_engine_count, asg_ok, asg_required=False):
    workforce_available = workforce_engine_count > 0
    required_ready = bool(database_ok and ollama_ok and (asg_ok or not asg_required))
    fully_operational = required_ready and workforce_available and asg_ok
    if not required_ready:
        status = "not_ready"
    elif not fully_operational:
        status = "degraded"
    else:
        status = "ready"
    return {
        "ok": required_ready,
        "live": True,
        "ready": required_ready,
        "status": status,
        "dependencies": {
            "chat_database": {"available": bool(database_ok), "required": True},
            "ollama": {"available": bool(ollama_ok), "required": True},
            "workforce": {
                "available": workforce_available,
                "engine_count": workforce_engine_count,
                "required": False,
            },
            "asg_core": {"available": bool(asg_ok), "required": bool(asg_required)},
        },
    }


def collect_health_report(database_path, ollama_url, workforce_engine_count, asg_base_url, asg_required=False):
    return build_health_report(
        database_ok=probe_database(database_path),
        ollama_ok=probe_ollama(ollama_url),
        workforce_engine_count=workforce_engine_count,
        asg_ok=probe_asg(asg_base_url),
        asg_required=asg_required,
    )
