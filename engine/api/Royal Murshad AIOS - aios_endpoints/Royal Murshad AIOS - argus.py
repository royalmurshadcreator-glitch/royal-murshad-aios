# argus.py — Argus router (P1B scaffold — NOT registered in aios_server.py yet)
# Registration deferred to P7 (master file is 2.14 GB, under investigation).
from fastapi import APIRouter
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_argus")
import argus_hub, argus_fusion, argus_reconstruct

router = APIRouter(prefix="/api/argus", tags=["argus"])

@router.get("/status")
def _status():
    return {
        "module": "aios_argus",
        "phase": "P1B",
        "hub": argus_hub.status(),
        "fusion": argus_fusion.status(),
        "reconstruct": argus_reconstruct.status(),
    }

@router.get("/scans")
def _scans():
    return {"scans": [], "note": "P2 will wire DB"}

@router.get("/entities")
def _entities():
    return {"entities": [], "note": "P2 will wire DB"}

@router.post("/scan")
def _scan():
    return {"status": "stub", "phase": "P1B", "message": "scan engine not implemented yet"}
