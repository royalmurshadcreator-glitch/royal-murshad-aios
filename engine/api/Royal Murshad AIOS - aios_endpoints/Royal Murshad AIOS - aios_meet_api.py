"""
aios_meet API + WebSocket signaling.
WS endpoint: /api/meet/ws/{room_id}/{peer_id}
Messages are JSON: {type: "offer"|"answer"|"ice"|"chat"|..., ...}
Server relays to all OTHER peers in the same room.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional, Dict, List
import sys, json, asyncio
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_meet")
import aios_meet as m

router = APIRouter(prefix="/api/meet", tags=["meet"])

# room_id -> { peer_id: WebSocket }
_WS: Dict[str, Dict[str, WebSocket]] = {}
_WS_LOCK = asyncio.Lock()


class RoomReq(BaseModel):
    title: str = ""
    host: str = ""

class JoinReq(BaseModel):
    peer_name: str = ""
    peer_id: Optional[str] = None


@router.get("/stats")
def _stats(): return m.stats()

@router.get("/rooms")
def _rooms(): return m.rooms()

@router.post("/rooms/new")
def _new_room(req: RoomReq): return m.create_room(req.title, req.host)

@router.get("/room/{rid}")
def _room(rid: str): return m.room_info(rid)

@router.post("/room/{rid}/close")
def _close(rid: str): return m.close_room(rid)

@router.post("/room/{rid}/join")
def _join(rid: str, req: JoinReq): return m.join(rid, req.peer_name, req.peer_id)

@router.post("/room/{rid}/leave/{pid}")
def _leave(rid: str, pid: str): return m.leave(rid, pid)

@router.get("/history")
def _hist(limit: int = 50): return m.history(limit)


# ── WebSocket signaling ──
@router.websocket("/ws/{room_id}/{peer_id}")
async def ws_signaling(ws: WebSocket, room_id: str, peer_id: str):
    await ws.accept()

    async with _WS_LOCK:
        if room_id not in _WS:
            _WS[room_id] = {}
        _WS[room_id][peer_id] = ws
        peers_now = list(_WS[room_id].keys())

    # tell this peer about existing peers
    await ws.send_json({"type": "peers", "peers": peers_now, "you": peer_id})

    # tell existing peers a new one joined
    for pid, sock in list(_WS[room_id].items()):
        if pid != peer_id:
            try:
                await sock.send_json({"type": "peer-joined", "peer_id": peer_id})
            except Exception:
                pass

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except Exception:
                msg = {"type": "raw", "data": raw}
            msg["from"] = peer_id
            # relay to all OTHER peers in room
            for pid, sock in list(_WS[room_id].items()):
                if pid == peer_id:
                    continue
                try:
                    await sock.send_json(msg)
                except Exception:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        async with _WS_LOCK:
            if room_id in _WS:
                _WS[room_id].pop(peer_id, None)
                if not _WS[room_id]:
                    _WS.pop(room_id, None)
        # tell remaining peers
        if room_id in _WS:
            for pid, sock in list(_WS[room_id].items()):
                try:
                    await sock.send_json({"type": "peer-left", "peer_id": peer_id})
                except Exception:
                    pass
