from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr

ROOT = Path(r"D:\01_PROJECTS\AIOS")
MASTER_DIR = ROOT / "01_SERVERS" / "master"
API_DIR = ROOT / "07_API"

for _path in (str(MASTER_DIR), str(API_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from aios_admin_control.storage_box import StorageBox

BOX_ROOT = ROOT / "04_MEMORY" / "aios_memory" / "data" / "storage_box"


def _auth_module():
    import auth
    return auth


def require_admin(royal_session: str | None = Cookie(default=None)) -> str:
    try:
        identity = _auth_module().whoami(royal_session or "")
    except Exception:
        raise HTTPException(status_code=401, detail="authentication_required")

    if not identity or not identity.get("ok"):
        raise HTTPException(status_code=401, detail="authentication_required")

    user = identity.get("user") or {}
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="admin_required")

    username = user.get("username")
    if not isinstance(username, str) or not username:
        raise HTTPException(status_code=401, detail="invalid_session_identity")
    return username


router = APIRouter(
    prefix="/api/admin/storage-box",
    tags=["owner-storage"],
)


class SecretCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    secret_id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=120)
    value: SecretStr = Field(min_length=1, max_length=8192)
    category: str = Field(default="general", min_length=1, max_length=60)


class ConfigSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    config: dict[str, Any]
    note: str = Field(default="", max_length=500)


class ConfigRestore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int = Field(ge=1)


def _box() -> StorageBox:
    return StorageBox(BOX_ROOT)


def _check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        return

    try:
        parsed = urlsplit(origin)
        origin_host = parsed.netloc.lower()
        request_host = (request.headers.get("host") or "").lower()

        if parsed.scheme not in ("http", "https") or not origin_host:
            raise ValueError("invalid origin")
        if not request_host or origin_host != request_host:
            raise HTTPException(status_code=403, detail="origin_not_allowed")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=403, detail="origin_not_allowed")


def _redact(value: Any) -> Any:
    sensitive = re.compile(
        r"^(?:password|secret|secret_value|plaintext|ciphertext|"
        r"ciphertext_b64|nonce|data_key|key_material|private_key|"
        r"credential|api_key|access_token|refresh_token|token|value)$",
        re.IGNORECASE,
    )
    if isinstance(value, dict):
        return {
            str(k): "[REDACTED]" if sensitive.fullmatch(str(k))
            else _redact(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return type(value).__name__


def _require_initialized(box: StorageBox) -> None:
    try:
        box._require_initialized()
    except Exception:
        raise HTTPException(
            status_code=409,
            detail="storage_box_not_initialized_or_unavailable",
        )


def _operation_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (ValueError, TypeError)):
        return HTTPException(status_code=400, detail="storage_box_request_rejected")
    if isinstance(exc, (KeyError, FileNotFoundError)):
        return HTTPException(status_code=404, detail="storage_box_record_not_found")
    return HTTPException(status_code=500, detail="storage_box_operation_failed")


def _validate_section(section: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", section):
        raise HTTPException(status_code=400, detail="invalid_config_section")


@router.get("/status")
def storage_status(actor: str = Depends(require_admin)):
    try:
        box = _box()
        return {"ok": True, "health": _redact(box.health())}
    except Exception as exc:
        raise _operation_error(exc)


@router.post("/initialize")
def initialize_storage(
    request: Request,
    actor: str = Depends(require_admin),
):
    _check_origin(request)
    try:
        box = _box()
        result = box.initialize()
        return {
            "ok": True,
            "result": _redact(result),
            "health": _redact(box.health()),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _operation_error(exc)


@router.get("/secrets")
def list_secrets(actor: str = Depends(require_admin)):
    try:
        box = _box()
        _require_initialized(box)
        return {"ok": True, "secrets": _redact(box.list_secrets())}
    except HTTPException:
        raise
    except Exception as exc:
        raise _operation_error(exc)


@router.post("/secrets")
def save_secret(
    body: SecretCreate,
    request: Request,
    actor: str = Depends(require_admin),
):
    _check_origin(request)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", body.secret_id):
        raise HTTPException(status_code=400, detail="invalid_secret_id")

    try:
        box = _box()
        _require_initialized(box)
        result = box.save_secret(
            body.secret_id,
            body.label,
            body.value.get_secret_value(),
            body.category,
            actor,
        )
        return {
            "ok": True,
            "secret_id": body.secret_id,
            "result": _redact(result),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _operation_error(exc)


@router.delete("/secrets/{secret_id}")
def delete_secret(
    secret_id: str,
    request: Request,
    actor: str = Depends(require_admin),
):
    _check_origin(request)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", secret_id):
        raise HTTPException(status_code=400, detail="invalid_secret_id")

    try:
        box = _box()
        _require_initialized(box)
        result = box.delete_secret(secret_id, actor)
        return {"ok": True, "secret_id": secret_id, "result": _redact(result)}
    except HTTPException:
        raise
    except Exception as exc:
        raise _operation_error(exc)


@router.get("/config/{section}")
def get_config(section: str, actor: str = Depends(require_admin)):
    _validate_section(section)
    try:
        box = _box()
        _require_initialized(box)
        data = box.get_config_section(section)
        return {
            "ok": True,
            "section": section,
            "version": data.get("version", 0),
            "config": _redact(data.get("config", {})),
            "updated_at": data.get("updated_at"),
            "actor": data.get("actor"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _operation_error(exc)


@router.put("/config/{section}")
def save_config(
    section: str,
    body: ConfigSave,
    request: Request,
    actor: str = Depends(require_admin),
):
    _check_origin(request)
    _validate_section(section)
    try:
        box = _box()
        _require_initialized(box)
        result = box.save_config_section(section, body.config, actor, body.note)
        return {"ok": True, "section": section, "result": _redact(result)}
    except HTTPException:
        raise
    except Exception as exc:
        raise _operation_error(exc)


@router.get("/config/{section}/history")
def config_history(section: str, actor: str = Depends(require_admin)):
    _validate_section(section)
    try:
        box = _box()
        _require_initialized(box)
        data = box.list_config_history(section)
        return {
            "ok": True,
            "section": section,
            "history": _redact(data.get("items", [])),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _operation_error(exc)


@router.post("/config/{section}/restore")
def restore_config(
    section: str,
    body: ConfigRestore,
    request: Request,
    actor: str = Depends(require_admin),
):
    _check_origin(request)
    _validate_section(section)
    try:
        box = _box()
        _require_initialized(box)
        result = box.restore_config_section(section, body.version, actor)
        if not result.get("ok"):
            if result.get("error") == "version_not_found":
                raise HTTPException(status_code=404, detail="config_version_not_found")
            raise HTTPException(status_code=400, detail="config_restore_rejected")
        return {"ok": True, "section": section, "result": _redact(result)}
    except HTTPException:
        raise
    except Exception as exc:
        raise _operation_error(exc)


@router.get("/audit/verify")
def verify_audit(actor: str = Depends(require_admin)):
    try:
        box = _box()
        _require_initialized(box)
        return {"ok": True, "verification": _redact(box.verify_audit_chain())}
    except HTTPException:
        raise
    except Exception as exc:
        raise _operation_error(exc)


@router.get("/audit/events")
def audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    actor: str = Depends(require_admin),
):
    try:
        box = _box()
        _require_initialized(box)
        return {"ok": True, "events": _redact(box.audit_events(limit))}
    except HTTPException:
        raise
    except Exception as exc:
        raise _operation_error(exc)