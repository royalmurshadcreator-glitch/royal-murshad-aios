"""
ROYAL JARVIS - Sovereign Passport HTTP API (Phase 4, collision-safe)
"""
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(r"D:\01_PROJECTS\AIOS")
TOOLS = ROOT / "06_TOOLS"
SP_DIR = TOOLS / "sovereign_passport"

_sp_str = str(SP_DIR)
_tools_str = str(TOOLS)
_root_str = str(ROOT)

# Ensure our dirs are at the FRONT of sys.path
for _p in (_sp_str, _tools_str, _root_str):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

# Evict any cached modules with our names but foreign paths
_OUR_NAMES = ("spec", "sign", "build", "verify", "apply", "passport_io")
_sp_norm = _sp_str.replace("\\", "/").lower()
for _n in _OUR_NAMES:
    _m = sys.modules.get(_n)
    if _m is None:
        continue
    _f = getattr(_m, "__file__", "") or ""
    if _sp_norm not in _f.replace("\\", "/").lower():
        try:
            del sys.modules[_n]
        except Exception:
            pass

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/passport", tags=["passport"])


def _sp():
    """Lazy import with fresh lookups every time."""
    # Re-affirm sys.path precedence
    for _p in (_sp_str, _tools_str):
        if _p in sys.path:
            sys.path.remove(_p)
        sys.path.insert(0, _p)
    import spec as _spec
    import passport_io as _io
    import sign as _sign
    import build as _build
    import verify as _verify
    import apply as _apply
    return {
        "spec": _spec, "io": _io, "sign": _sign,
        "build": _build, "verify": _verify, "apply": _apply,
    }


class BuildReq(BaseModel):
    owner: str = "Royal Murshad"
    tags: list[str] = ["primary"]
    encrypt: bool = False
    passphrase: str | None = None
    include: list[str] | None = None
    exclude: list[str] | None = None


class VerifyReq(BaseModel):
    path: str
    passphrase: str | None = None


class ApplyReq(BaseModel):
    path: str
    confirm: bool = False
    passphrase: str | None = None


@router.get("/health")
def passport_health():
    try:
        m = _sp()
        return {
            "ok": True,
            "module": "sovereign_passport",
            "schema_version": m["spec"].SCHEMA_VERSION,
            "passport_dir": str(m["io"].PASSPORT_DIR),
            "keys_dir": str(m["io"].KEYS_DIR),
            "spec_file": getattr(m["spec"], "__file__", None),
            "sign_file": getattr(m["sign"], "__file__", None),
            "build_file": getattr(m["build"], "__file__", None),
        }
    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e)[:300], "trace": traceback.format_exc()[-1500:]}


@router.post("/keygen")
def passport_keygen(force: bool = False):
    try:
        return _sp()["sign"].generate_keypair(force=force)
    except Exception as e:
        raise HTTPException(500, f"keygen error: {str(e)[:200]}")


@router.post("/build")
def passport_build(req: BuildReq):
    try:
        m = _sp()
        pp = m["build"].build_passport(
            include=req.include, exclude=req.exclude,
            owner_name=req.owner, tags=req.tags,
        )
        pp = m["sign"].sign_passport(pp)
        pid = pp["passport"]["passport_id"]
        ts = pp["passport"]["created_at"].replace(":", "").replace("-", "").replace(".", "")[:15]
        ext = ".enc.json" if req.encrypt else ".json"
        path = m["io"].PASSPORT_DIR / (pid + "_" + ts + ext)
        r = m["io"].save_passport(pp, path, encrypt=req.encrypt, passphrase=req.passphrase)
        m["io"].append_index({
            "passport_id": pid, "path": str(path),
            "created_at": pp["passport"]["created_at"],
            "encrypted": bool(req.encrypt),
        })
        return r
    except Exception as e:
        import traceback
        raise HTTPException(500, f"build error: {str(e)[:300]} | {traceback.format_exc()[-800:]}")


@router.get("/list")
def passport_list(limit: int = 50):
    try:
        return {"ok": True, "items": _sp()["io"].read_index(limit=int(limit))}
    except Exception as e:
        import traceback
        raise HTTPException(500, f"list error: {str(e)[:300]} | {traceback.format_exc()[-800:]}")


@router.post("/info")
def passport_info(req: VerifyReq):
    try:
        pp = _sp()["io"].load_passport(req.path, passphrase=req.passphrase)
        p = pp.get("passport", {})
        s = pp.get("signature", {})
        return {
            "ok": True,
            "passport_id": p.get("passport_id"),
            "created_at": p.get("created_at"),
            "owner": p.get("owner"),
            "sections": list((p.get("sections") or {}).keys()),
            "signature_algo": s.get("algorithm"),
            "canonical_sha256": s.get("canonical_sha256"),
        }
    except Exception as e:
        raise HTTPException(500, f"info error: {str(e)[:200]}")


@router.post("/verify")
def passport_verify(req: VerifyReq):
    try:
        m = _sp()
        pp = m["io"].load_passport(req.path, passphrase=req.passphrase)
        return m["verify"].verify_passport(pp)
    except Exception as e:
        raise HTTPException(500, f"verify error: {str(e)[:200]}")


@router.post("/apply")
def passport_apply(req: ApplyReq):
    try:
        m = _sp()
        pp = m["io"].load_passport(req.path, passphrase=req.passphrase)
        vr = m["verify"].verify_passport(pp)
        if not vr.get("ok"):
            raise HTTPException(400, f"passport failed verification: {vr}")
        return m["apply"].apply_passport(pp, confirm=req.confirm)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"apply error: {str(e)[:200]}")


print("[sovereign-passport] API loaded (collision-safe)")
