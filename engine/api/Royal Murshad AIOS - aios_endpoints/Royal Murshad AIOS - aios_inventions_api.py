"""ROYAL JARVIS - Inventions Facade (Phase 10, collision-safe)

Unifies the six shipped inventions into one investor-facing surface:
  1. Sovereign Passport    -> 03_MEMORY/data/passports/
  2. Silence Protocol      -> 03_MEMORY/data/silence/silence_chains.jsonl
  3. Causal Diary          -> 03_MEMORY/data/causal_diary/causal_diary_chains.jsonl
  4. Confidence Integrity  -> 03_MEMORY/data/confidence_integrity/ci_chains.jsonl
  5. Refusal Negotiation   -> 03_MEMORY/data/refusal_negotiation/rn_chains.jsonl
  6. Regret Ledger         -> 03_MEMORY/data/regret_ledger/rl_chains.jsonl

Also:
  - verify-all   : recompute every chain
  - export-bundle: ed25519-signed manifest of all 6 chain head hashes
  - console      : single-page HTML operator view
"""
from __future__ import annotations
import sys, json, hashlib, base64, os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"D:\\01_PROJECTS\\AIOS")
TOOLS = ROOT / "06_TOOLS"
SP_DIR = TOOLS / "sovereign_passport"

for _p in (str(ROOT), str(TOOLS), str(SP_DIR)):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/inventions", tags=["inventions"])

CHAIN_DIR = ROOT / "04_MEMORY" / "aios_memory" / "data"

INVENTIONS = {
    "sovereign_passport": {
        "label": "Sovereign Passport",
        "phase": 4,
        "type": "files",
        "dir": CHAIN_DIR / "passports",
        "endpoint": "/api/passport/*",
    },
    "silence_protocol": {
        "label": "Silence Protocol",
        "phase": 5,
        "type": "chain",
        "file": CHAIN_DIR / "silence" / "silence_chains.jsonl",
        "endpoint": "/api/silence/*",
    },
    "causal_diary": {
        "label": "Causal Diary",
        "phase": 6,
        "type": "chain",
        "file": CHAIN_DIR / "causal_diary" / "causal_diary_chains.jsonl",
        "endpoint": "/api/causal-diary/*",
    },
    "confidence_integrity": {
        "label": "Confidence Integrity",
        "phase": 7,
        "type": "chain",
        "file": CHAIN_DIR / "confidence_integrity" / "ci_chains.jsonl",
        "endpoint": "/api/confidence-integrity/*",
    },
    "refusal_negotiation": {
        "label": "Refusal Negotiation",
        "phase": 8,
        "type": "chain",
        "file": CHAIN_DIR / "refusal_negotiation" / "rn_chains.jsonl",
        "endpoint": "/api/refusal-negotiation/*",
    },
    "regret_ledger": {
        "label": "Regret Ledger",
        "phase": 9,
        "type": "chain",
        "file": CHAIN_DIR / "regret_ledger" / "rl_chains.jsonl",
        "endpoint": "/api/regret-ledger/*",
    },
}

_CANON = {"sort_keys": True, "separators": (",", ":"), "default": str}


def _read_jsonl(path, limit=100000):
    if not Path(path).exists():
        return []
    try:
        lines = Path(path).read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(l) for l in lines[-limit:] if l.strip()]
    except Exception:
        return []


def _last_hash(path):
    if not Path(path).exists():
        return ""
    try:
        recs = _read_jsonl(path, limit=1)
        return recs[-1].get("hash", "") if recs else ""
    except Exception:
        return ""


def _verify_chain(path):
    if not Path(path).exists():
        return {"ok": True, "total": 0, "breaks": [], "mismatches": []}
    recs = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except Exception:
                    pass
    breaks, mismatches = [], []
    for i in range(1, len(recs)):
        if recs[i - 1].get("hash", "") != recs[i].get("prev_hash", ""):
            breaks.append(i)
    for i, r in enumerate(recs):
        stored = r.get("hash")
        e = dict(r); e.pop("hash", None); prev = e.pop("prev_hash", None); e.pop("id", None)
        canonical = json.dumps(e, **_CANON)
        recomputed = hashlib.sha256(((prev or "") + canonical).encode("utf-8")).hexdigest()
        if recomputed != stored:
            mismatches.append(i)
    return {
        "ok": len(breaks) == 0 and len(mismatches) == 0,
        "total": len(recs),
        "breaks": breaks[:10],
        "mismatches": mismatches[:10],
    }


def _chain_status(key, meta):
    if meta["type"] == "chain":
        f = meta["file"]
        return {
            "key": key, "label": meta["label"], "phase": meta["phase"],
            "endpoint": meta["endpoint"], "type": "chain",
            "exists": Path(f).exists(),
            "records": len(_read_jsonl(f, limit=100000)),
            "head_hash": _last_hash(f),
            "file": str(f),
        }
    # files (passports)
    d = meta["dir"]
    files = list(d.glob("*.json")) if Path(d).exists() else []
    return {
        "key": key, "label": meta["label"], "phase": meta["phase"],
        "endpoint": meta["endpoint"], "type": "files",
        "exists": Path(d).exists(),
        "records": len(files),
        "head_hash": hashlib.sha256(
            "|".join(sorted(f.name for f in files)).encode("utf-8")
        ).hexdigest()[:32] if files else "",
        "file": str(d),
    }


def _sign_bundle(bundle_dict):
    """Sign the canonicalized bundle with the Sovereign Passport ed25519 key."""
    try:
        if str(SP_DIR) not in sys.path:
            sys.path.insert(0, str(SP_DIR))
        import sign as pp_sign
        payload = json.dumps(bundle_dict, **_CANON).encode("utf-8")
        priv = pp_sign.load_private_key()
        sig = priv.sign(payload)
        pub_raw = priv.public_key().public_bytes(
            encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.Raw,
            format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["PublicFormat"]).PublicFormat.Raw,
        )
        return {
            "algorithm": "ed25519",
            "public_key": base64.b64encode(pub_raw).decode("ascii"),
            "value": base64.b64encode(sig).decode("ascii"),
            "canonical_sha256": hashlib.sha256(payload).hexdigest(),
        }
    except Exception as e:
        return {"error": str(e)[:300]}


@router.get("/health")
def inv_health():
    items = [_chain_status(k, v) for k, v in INVENTIONS.items()]
    total_records = sum(i["records"] for i in items)
    return {
        "ok": True,
        "product": "Royal Jarvis AIOS - Six Inventions",
        "schema_version": "1.0",
        "inventions": items,
        "count": len(items),
        "total_records": total_records,
    }


@router.get("/portfolio")
def inv_portfolio():
    items = [_chain_status(k, v) for k, v in INVENTIONS.items()]
    by_phase = {}
    for i in items:
        by_phase[f"phase{i['phase']}"] = {
            "label": i["label"], "records": i["records"],
            "head_hash_prefix": (i["head_hash"] or "")[:12],
        }
    return {
        "ok": True,
        "count": len(items),
        "total_records": sum(i["records"] for i in items),
        "by_phase": by_phase,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/verify-all")
def inv_verify_all():
    results = {}
    all_ok = True
    for k, v in INVENTIONS.items():
        if v["type"] == "chain":
            r = _verify_chain(v["file"])
            results[k] = r
            if not r["ok"]:
                all_ok = False
        else:
            # files: "verify" = list exists and >0 files
            files = list(v["dir"].glob("*.json")) if v["dir"].exists() else []
            results[k] = {"ok": len(files) > 0, "total": len(files), "files": True}
    return {"ok": all_ok, "chains": results,
            "generated_at": datetime.now(timezone.utc).isoformat()}


class BundleReq(BaseModel):
    note: str = ""


@router.post("/export-bundle")
def inv_export_bundle(req: BundleReq):
    items = [_chain_status(k, v) for k, v in INVENTIONS.items()]
    verify = inv_verify_all()
    bundle_body = {
        "bundle_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": req.note[:400],
        "inventions": [
            {
                "key": i["key"], "label": i["label"], "phase": i["phase"],
                "records": i["records"], "head_hash": i["head_hash"],
                "chain_verified": verify["chains"].get(i["key"], {}).get("ok", False),
            } for i in items
        ],
        "total_records": sum(i["records"] for i in items),
    }
    signature = _sign_bundle(bundle_body)
    return {"ok": "error" not in signature, "bundle": bundle_body, "signature": signature}


@router.get("/console", response_class=HTMLResponse)
def inv_console():
    p = ROOT / "static" / "inventions.html"
    if p.exists():
        return HTMLResponse(p.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>inventions.html missing</h1>", status_code=404)


print("[inventions] facade loaded (6-invention unified surface)")
