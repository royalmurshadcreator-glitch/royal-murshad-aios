# antarctica.py — public router (NOT registered in aios_server.py yet)
from fastapi import APIRouter
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_antarctica")
import antarctica_api as a

router = APIRouter(prefix="/api/antarctica", tags=["antarctica"])

@router.get("/status")
def _status(): return a.status()

@router.get("/layers/synthetic")
def _layers_synthetic():
    import antarctica_layers as L
    layers, total = L.synthetic_column()
    issues = L.verify_column(layers)
    return {"layers": layers, "total_depth_m": total, "issues": issues}

@router.get("/scans")
def _scans(): return {"scans": [], "note": "P2 wires DB"}
