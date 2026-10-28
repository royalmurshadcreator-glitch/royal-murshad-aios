"""
Royal Jarvis ? Executor Config API
==================================
Read/write the executor's whitelist, blacklist, and mode.
Endpoints:
  GET  /api/executor/config              ? read current config
  POST /api/executor/config/section/{s}  ? update a section
  POST /api/executor/config/reset        ? restore defaults
  GET  /api/executor/config/file         ? show where it's stored
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

EXEC_CONFIG_FILE = Path(r"D:\01_PROJECTS\AIOS\12_WORKSPACE\executor\config.json")
_LOCK = threading.Lock()

DEFAULTS: dict[str, Any] = {
    "mode": "safe",
    "allowed_apps": [],
    "allowed_roots": [],
    "blocked_keywords": [],
    "blocked_path_segments": [],
    "max_commands_per_hour": 60,
    "max_commands_per_second_interval": 2.0,
    "max_writes_per_minute": 3,
}

ALLOWED_SECTIONS = set(DEFAULTS.keys())


def _read() -> dict[str, Any]:
    if not EXEC_CONFIG_FILE.exists():
        EXEC_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _write(DEFAULTS)
        return json.loads(json.dumps(DEFAULTS))
    try:
        with EXEC_CONFIG_FILE.open("r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("root not an object")
        # merge defaults so missing keys don't break the frontend
        merged = json.loads(json.dumps(DEFAULTS))
        merged.update(data)
        return merged
    except (OSError, json.JSONDecodeError, ValueError):
        return json.loads(json.dumps(DEFAULTS))


def _write(data: dict[str, Any]) -> None:
    EXEC_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = EXEC_CONFIG_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8-sig") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, EXEC_CONFIG_FILE)


def load() -> dict[str, Any]:
    with _LOCK:
        return _read()


def update_section(name: str, value: Any) -> dict[str, Any]:
    if name not in ALLOWED_SECTIONS:
        raise ValueError(f"unknown section: {name}")
    with _LOCK:
        data = _read()
        data[name] = value
        _write(data)
        return data


def reset() -> dict[str, Any]:
    with _LOCK:
        _write(DEFAULTS)
        return json.loads(json.dumps(DEFAULTS))


router = APIRouter(prefix="/api/executor/config", tags=["executor-config"])


class SectionBody(BaseModel):
    value: object


@router.get("")
def read_config():
    cfg = load()
    return {
        "ok": True,
        "config": cfg,
        "file": str(EXEC_CONFIG_FILE),
    }


@router.post("/section/{section}")
def update_section_route(section: str, body: SectionBody):
    try:
        cfg = update_section(section, body.value)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True, "section": section, "config": cfg}


@router.post("/reset")
def reset_config():
    cfg = reset()
    return {"ok": True, "config": cfg}


@router.get("/file")
def config_file_path():
    return {
        "ok": True,
        "path": str(EXEC_CONFIG_FILE),
        "exists": EXEC_CONFIG_FILE.exists(),
    }
