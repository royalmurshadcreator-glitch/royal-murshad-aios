"""AIOS Live Server — FastAPI + WebSocket on 127.0.0.1:8093.
Phase 3: Backend only. Frontend robot UI ships in Phase 4.
"""
import sys, json, asyncio
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager

ROOT = Path(r"D:\01_PROJECTS\AIOS")
LEADS = ROOT / "06_TOOLS" / "aios_leads"
UI_DIR = ROOT / "14_UI" / "jarvis_live"
LOG = ROOT / "10_LOGS" / "jarvis" / "live_server.log"
LOG.parent.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(LEADS))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ---- lazy router import (so startup doesn't fail if a module is missing) ----
_router = None
def _get_router():
    global _router
    if _router is None:
        try:
            import aios_jarvis_router as R
            _router = R
        except Exception as e:
            _log(f"router import failed: {e}")
    return _router

def _log(msg):
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now(timezone.utc).isoformat()}] {msg}\n")
    except Exception:
        pass

def _route_text(text: str) -> str:
    """Route a text command through the existing Jarvis router."""
    if not text:
        return "(empty)"
    R = _get_router()
    if not R:
        return "Router unavailable"
    try:
        reply = R.route(text)
        return str(reply) if reply else "(no reply)"
    except Exception as e:
        return f"Error: {str(e)[:200]}"

# ---- WebSocket connection manager ----
class Hub:
    def __init__(self):
        self.clients: list[WebSocket] = []
    async def join(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)
    def leave(self, ws: WebSocket):
        if ws in self.clients:
            self.clients.remove(ws)
    async def broadcast(self, msg: str):
        dead = []
        for c in self.clients:
            try: await c.send_text(msg)
            except Exception: dead.append(c)
        for c in dead: self.leave(c)

hub = Hub()

# ---- lifespan: log startup ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    _log("=" * 60)
    _log("AIOS Live Server starting")
    yield
    _log("AIOS Live Server stopping")

app = FastAPI(title="AIOS Live Server", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# HTTP ROUTES
# ================================================================
@app.get("/")
@app.get("/avatar")
def avatar():
    """Serve the avatar HTML UI."""
    p = UI_DIR / "index.html"
    if not p.exists():
        return HTMLResponse("<h1>UI not found</h1><p>Run Phase 4 to build it.</p>", status_code=404)
    return HTMLResponse(p.read_text(encoding="utf-8"))

@app.get("/api/health")
def health():
    R = _get_router()
    return {
        "ok": True,
        "router": R is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "clients": len(hub.clients),
    }

@app.post("/api/route")
async def route_api(req: Request):
    """Accept JSON {text: "..."} → returns {reply: "..."}"""
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"error": "invalid JSON"}, status_code=400)
    text = (body.get("text") or "").strip()
    if not text:
        return JSONResponse({"error": "empty text"}, status_code=400)
    _log(f"route: {text[:80]}")
    reply = _route_text(text)
    # Also broadcast to any WS clients
    try:
        await hub.broadcast(json.dumps({"type": "reply", "text": reply}))
    except Exception:
        pass
    return {"reply": reply, "ts": datetime.now(timezone.utc).isoformat()}

@app.get("/api/mode")
def mode_api():
    """Return current master mode."""
    try:
        p = ROOT / "10_LOGS" / "jarvis" / "master_mode.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"mode": "unknown"}

# ================================================================
# WEBSOCKET
# ================================================================
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await hub.join(ws)
    _log(f"ws client connected (total {len(hub.clients)})")
    try:
        await ws.send_text(json.dumps({
            "type": "hello",
            "message": "AIOS Live Server connected",
            "ts": datetime.now(timezone.utc).isoformat()
        }))
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
                text = (data.get("text") or "").strip()
            except Exception:
                text = raw.strip()
            if not text:
                continue
            _log(f"ws route: {text[:80]}")
            reply = _route_text(text)
            await ws.send_text(json.dumps({
                "type": "reply",
                "text": reply,
                "ts": datetime.now(timezone.utc).isoformat()
            }))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        _log(f"ws error: {e}")
    finally:
        hub.leave(ws)
        _log(f"ws client disconnected (total {len(hub.clients)})")

# ================================================================
# MAIN
# ================================================================
if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8093
    _log(f"binding 127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")