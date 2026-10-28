"""
ROYAL JARVIS â€” Thought Engine HTTP API (Phase 20)
Mounts /api/thought/* endpoints. Calls 11_TOOLS/thought_engine.py.
Read-only except POST /api/thought/infer (which persists a snapshot).
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Optional
import sys

ROOT = Path(r"D:\\01_PROJECTS\\AIOS")
TOOLS = ROOT / "06_TOOLS"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

router = APIRouter(prefix="/api/thought", tags=["thought-engine"])


def _te():
    """Lazy import â€” avoids startup cost if unused."""
    import thought_engine as te
    return te


@router.get("/current")
def thought_current():
    """Latest persisted snapshot."""
    try:
        r = _te().latest_snapshot()
        return r
    except Exception as e:
        raise HTTPException(500, f"thought_engine error: {str(e)[:200]}")


@router.get("/history")
def thought_history(limit: int = 20):
    """Recent snapshots (metadata only)."""
    try:
        r = _te().list_snapshots(limit=int(limit))
        return r
    except Exception as e:
        raise HTTPException(500, f"thought_engine error: {str(e)[:200]}")


@router.post("/infer")
def thought_infer(refresh: bool = True, source: str = "api"):
    """Force a fresh cognitive pass. Persists a snapshot."""
    try:
        r = _te().think(refresh=bool(refresh), persist=True, source=source)
        return r
    except Exception as e:
        raise HTTPException(500, f"thought_engine error: {str(e)[:200]}")


@router.get("/stats")
def thought_stats():
    """Aggregate counts + avg confidence + durations."""
    try:
        return _te().stats()
    except Exception as e:
        raise HTTPException(500, f"thought_engine error: {str(e)[:200]}")


@router.get("/snapshot/{sid}")
def thought_snapshot_detail(sid: int):
    """Full snapshot by id (from list)."""
    try:
        import sqlite3, json
        conn = sqlite3.connect(str(ROOT / "04_MEMORY" / "aios_memory" / "royal_memory.db"))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM thought_snapshots WHERE id=?", (int(sid),)).fetchone()
        conn.close()
        if not row:
            raise HTTPException(404, "snapshot not found")
        d = dict(row)
        # decode JSON columns
        for k in ("verification","metacognition","state_json"):
            try:
                d[k] = json.loads(d.get(k) or "{}")
            except Exception:
                pass
        return {"ok": True, "snapshot": d}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"error: {str(e)[:200]}")

# ============ PHASE 24-25 ENDPOINTS (consensus + learner) ============

@router.post("/reconstruct")
def thought_reconstruct(persist: bool = True, source: str = "api"):
    """Run the Phase 24 consensus engine and return the fused thought."""
    try:
        import sys as _sys
        _TOOLS = str(ROOT / "06_TOOLS")
        if _TOOLS not in _sys.path:
            _sys.path.insert(0, _TOOLS)
        import thought_consensus as tc
        r = tc.reconstruct(persist=bool(persist), source=source)
        return r
    except Exception as e:
        raise HTTPException(500, f"consensus error: {str(e)[:200]}")


@router.get("/consensus/current")
def thought_consensus_current():
    """Latest consensus snapshot."""
    try:
        import sys as _sys
        _TOOLS = str(ROOT / "06_TOOLS")
        if _TOOLS not in _sys.path:
            _sys.path.insert(0, _TOOLS)
        import thought_consensus as tc
        return tc.latest_consensus()
    except Exception as e:
        raise HTTPException(500, f"consensus error: {str(e)[:200]}")


@router.get("/consensus/history")
def thought_consensus_history(limit: int = 20):
    """Recent consensus snapshots."""
    try:
        import sys as _sys
        _TOOLS = str(ROOT / "06_TOOLS")
        if _TOOLS not in _sys.path:
            _sys.path.insert(0, _TOOLS)
        import thought_consensus as tc
        return tc.list_consensus(limit=int(limit))
    except Exception as e:
        raise HTTPException(500, f"consensus error: {str(e)[:200]}")


@router.get("/weights")
def thought_weights():
    """Current adaptive weights from the Phase 25 learner."""
    try:
        import sys as _sys
        _TOOLS = str(ROOT / "06_TOOLS")
        if _TOOLS not in _sys.path:
            _sys.path.insert(0, _TOOLS)
        import thought_learner as tl
        return tl.current_weights()
    except Exception as e:
        raise HTTPException(500, f"learner error: {str(e)[:200]}")


@router.post("/weights/apply")
def thought_weights_apply():
    """Push learner weights into the live consensus engine (in-memory)."""
    try:
        import sys as _sys
        _TOOLS = str(ROOT / "06_TOOLS")
        if _TOOLS not in _sys.path:
            _sys.path.insert(0, _TOOLS)
        import thought_learner as tl
        return tl.apply_to_consensus()
    except Exception as e:
        raise HTTPException(500, f"learner error: {str(e)[:200]}")


@router.post("/learn")
def thought_learn(allow_repeat: bool = False):
    """Run one Phase 25 learning cycle (compares consensus vs tasks.json)."""
    try:
        import sys as _sys
        _TOOLS = str(ROOT / "06_TOOLS")
        if _TOOLS not in _sys.path:
            _sys.path.insert(0, _TOOLS)
        import thought_learner as tl
        return tl.evaluate_once(source="api", allow_repeat=bool(allow_repeat))
    except Exception as e:
        raise HTTPException(500, f"learner error: {str(e)[:200]}")
