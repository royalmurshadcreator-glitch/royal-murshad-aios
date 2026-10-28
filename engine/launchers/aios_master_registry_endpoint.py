"""Master Registry API — serves the whole system map."""
from fastapi import APIRouter
import json, os
from pathlib import Path

router = APIRouter(tags=["master-registry"])

MASTER_FILE = Path(r"D:\01_PROJECTS\Royal Murshad AIOS\MASTER_REGISTRY.json")

@router.get("/api/master/registry")
def master_registry():
    if not MASTER_FILE.exists():
        return {"ok": False, "error": "master registry not created yet"}
    try:
        data = json.loads(MASTER_FILE.read_text(encoding="utf-8"))
        return {"ok": True, **data}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/api/master/systems")
def master_systems():
    """Quick summary of all subsystems."""
    return {
        "ok": True,
        "systems": {
            "core": ["apps", "agents", "divisions", "chat", "tasks", "tools"],
            "vision": ["brain_reading", "gesture_vision", "eye_tracking", "passport_crypto"],
            "neural": ["silence", "refusal_negotiation", "confidence_integrity",
                       "regret_ledger", "causal_diary", "screen_live", "emotion_fusion"],
            "business": ["store", "auth", "stripe", "dropship", "crm"],
            "inventions": ["52_documented_inventions", "29_agent_spawned"],
            "physical": ["awaiting_user_data"],
            "productivity": ["calendar", "contacts", "sheets", "slides",
                             "photos", "maps", "meet", "news", "social", "forum",
                             "knowledge", "errorlog", "guardrails", "backup",
                             "executor", "stomach", "power"],
        }
    }
