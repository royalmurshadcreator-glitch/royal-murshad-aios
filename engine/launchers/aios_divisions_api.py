"""Divisions API — serves the unified 187-division registry."""
from fastapi import APIRouter, HTTPException
import json
from pathlib import Path

router = APIRouter(tags=["divisions"])

# Prefer unified; fallback to detailed; fallback to basic
DIV_REGISTRY_FILES = [
    r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - DIVISIONS\_unified_registry.json",
    r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - DIVISIONS\Royal Murshad AIOS - _registry.json",
    r"D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - DIVISIONS\_registry.json",
]

def _load_divisions():
    for p in DIV_REGISTRY_FILES:
        path = Path(p)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
                divs = data.get("divisions", [])
                if divs:
                    return divs, str(path)
            except Exception:
                pass
    return [], None

@router.get("/api/divisions/list")
def list_divisions():
    divs, src = _load_divisions()
    return {"ok": True, "total": len(divs), "source": src, "divisions": divs}

@router.get("/api/divisions/stats")
def division_stats():
    divs, src = _load_divisions()
    by_cat = {}
    by_status = {}
    for d in divs:
        cat = d.get("category", "UNCATEGORIZED")
        st = d.get("status", "unknown")
        by_cat[cat] = by_cat.get(cat, 0) + 1
        by_status[st] = by_status.get(st, 0) + 1
    return {
        "ok": True,
        "total": len(divs),
        "source": src,
        "by_category": by_cat,
        "by_status": by_status,
        "linked": by_status.get("linked", 0),
        "stubbed": by_status.get("stub", 0),
        "disabled": by_status.get("disabled", 0),
    }

@router.get("/api/divisions/{div_id}")
def get_division(div_id: str):
    divs, _ = _load_divisions()
    for d in divs:
        if str(d.get("id")) == div_id or d.get("name", "").lower() == div_id.lower() or d.get("folder", "") == div_id:
            return {"ok": True, "division": d}
    raise HTTPException(404, f"division not found: {div_id}")
