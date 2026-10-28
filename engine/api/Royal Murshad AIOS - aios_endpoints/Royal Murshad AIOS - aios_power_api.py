"""ROYAL JARVIS - POWER API (FastAPI router)"""
from fastapi import APIRouter
from aios_power_control import (
    status_all, power_on, power_off, power_restart, single_action,
    cleanup_preview, cleanup_run
)

router = APIRouter(prefix="/api/power", tags=["power"])

@router.get("/status")
def api_status(): return status_all()

@router.post("/on")
def api_on(): return power_on()

@router.post("/off")
def api_off(): return power_off()

@router.post("/restart")
def api_restart(): return power_restart()

@router.post("/service/{name}/on")
def api_service_on(name: str): return single_action(name, "on")

@router.post("/service/{name}/off")
def api_service_off(name: str): return single_action(name, "off")

@router.get("/cleanup/preview")
def api_cleanup_preview(): return cleanup_preview()

@router.post("/cleanup/run")
def api_cleanup_run(kill_chrome: bool = True, kill_edge: bool = False):
    return cleanup_run(kill_chrome=kill_chrome, kill_edge=kill_edge)