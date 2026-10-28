"""
ROYAL JARVIS - VOICE API (v1.0)
Endpoints:
  POST /api/voice/listen   -> audio file -> Whisper -> text
  POST /api/voice/ask      -> text -> LLM -> {reply, action}
  POST /api/voice/task     -> fire-and-forget task to orchestrator
"""
from __future__ import annotations
import io, json, subprocess, sys, time, urllib.request
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from pydantic import BaseModel

ROOT = Path(r"D:\\01_PROJECTS\\AIOS")
PY   = ROOT / ".venv" / "Scripts" / "python.exe"

OLLAMA_URL   = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"
SPEAK_URL    = "http://127.0.0.1:9000/api/service/speak"
ORCH_URL     = "http://127.0.0.1:9100/api/orchestrator/tasks"

router = APIRouter(prefix="/api/voice", tags=["voice"])

# --- inject voice dispatcher path (added by patch) ---
import sys as _sys
_voice_dir = str(ROOT / "12_WORKSPACE" / "aios_voice_bot")
if _voice_dir not in _sys.path:
    _sys.path.insert(0, _voice_dir)
# --- end inject ---

_whisper_model = None

def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
            print("[voice] whisper small loaded")
        except Exception as e:
            print(f"[voice] whisper load failed: {e}")
            _whisper_model = False
    return _whisper_model

class AskIn(BaseModel):
    text: str
    session_id: Optional[str] = None

class TaskIn(BaseModel):
    action: str
    args: dict = {}

@router.post("/listen")
async def listen(audio: UploadFile = File(...), session_id: str = Form("default")):
    try:
        data = await audio.read()
    except Exception as e:
        raise HTTPException(400, f"read failed: {e}")

    if not data or len(data) < 100:
        return {"ok": False, "text": "", "error": "empty_audio"}

    model = _get_whisper()
    if not model:
        return {"ok": False, "error": "whisper_unavailable"}

    tmp = ROOT / "Logs" / "voice_in.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(data)

    try:
        segments, info = model.transcribe(str(tmp), beam_size=1, language="en")
        text = " ".join(s.text for s in segments).strip()
    except Exception as e:
        return {"ok": False, "error": f"transcribe_failed: {e}"}

    return {"ok": True, "text": text, "language": info.language,
            "duration": info.duration}

@router.post("/ask")
def ask(body: AskIn):
    """
    Route through the real dispatcher (brain + executor).
    Two modes:
      - chat   : no computer action, just a friendly reply
      - task   : dispatcher ran an action through the executor
    """
    text = (body.text or "").strip()
    # v21 fix: try jarvis python fast-path FIRST (services/money/agents/status)
    try:
        import sys as _sys21, os as _os21
        _ask_dir = r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_leads"
        if _ask_dir not in _sys21.path:
            _sys21.path.insert(0, _ask_dir)
        import aios_jarvis_ask as _jask
        _fast = _jask.python_answer(text)
        if _fast:
            return {"ok": True, "mode": "chat", "reply": _fast,
                    "intent": "fast-path", "action": None,
                    "detail": {"source": "python_answer", "confidence": 1.0}}
    except Exception as _e21:
        # do not fail the whole request on fast-path error; fall through
        pass
    if not text:
        return {"ok": False, "mode": "chat", "reply": "I didn't hear anything.",
                "action": None, "detail": None}

    try:
        from dispatcher import dispatch as _dispatch
    except Exception as e:
        return {"ok": False, "mode": "chat",
                "reply": "Voice dispatcher not available.",
                "action": None, "error": str(e)}

    try:
        result = _dispatch(text)
    except Exception as e:
        return {"ok": False, "mode": "chat",
                "reply": "Something went wrong in the dispatcher.",
                "action": None, "error": str(e)}

    detail = result.get("detail") or {}
    intent = (detail.get("intent") if isinstance(detail, dict) else None) or ""

    # v1.1 fix: check for action in detail OR top-level result
    has_action = False
    if isinstance(detail, dict) and detail.get("action"):
        has_action = True
    if result.get("action"):
        has_action = True

    # decide mode: prefer explicit action over intent
    if has_action:
        mode = "task"
    elif intent in ("greeting", "meta", "unknown", "stop") or not intent:
        mode = "chat"
    else:
        mode = "task"

    return {
        "ok": result.get("ok", False),
        "mode": mode,
        "reply": result.get("reply", ""),
        "intent": intent,
        "action": intent if mode == "task" else None,
        "detail": detail,
    }

@router.post("/task")
async def task(body: TaskIn):
    try:
        payload = json.dumps({"action": body.action, "args": body.args}).encode()
        req = urllib.request.Request(ORCH_URL, data=payload,
              headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read())
        return {"ok": True, "queued": True, "orchestrator": result}
    except Exception as e:
        try:
            sys.path.insert(0, str(ROOT / "12_WORKSPACE" / "aios_voice_bot"))
            from dispatcher import dispatch
            dispatch(body.action)
            return {"ok": True, "queued": True, "via": "direct"}
        except Exception as e2:
            return {"ok": False, "error": f"{e} / {e2}"}

# --- health + status + speak (added) ---
class SpeakIn(BaseModel):
    text: str

@router.get("/health")
def health():
    return {
        "ok": True,
        "service": "voice_api",
        "whisper_loaded": _whisper_model is not None and _whisper_model is not False,
        "ollama_model": OLLAMA_MODEL,
    }

@router.get("/status")
def status():
    return {
        "ok": True,
        "whisper": "loaded" if (_whisper_model is not None and _whisper_model is not False) else "not_loaded",
        "dispatcher_available": True,
        "endpoints": ["/listen", "/ask", "/task", "/speak", "/health", "/status"],
    }

@router.post("/speak")
def speak(body: SpeakIn):
    """Speak text via Windows SAPI (PowerShell)."""
    import subprocess
    clean = body.text.replace("'", "").replace('"', "")
    ps = ("Add-Type -AssemblyName System.Speech; "
          "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('" + clean + "')")
    try:
        subprocess.Popen(["powershell", "-Command", ps],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True, "spoken": len(clean)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
# --- end health + status + speak ---


# --- unified voice pipeline (Phase 2, added 2026-10-02) ---
@router.post("/pipeline")
async def pipeline(audio: UploadFile = File(...), session_id: str = Form("default")):
    """
    Unified voice -> action -> voice flow.
    Accepts audio file, returns transcript + action result + spoken reply.
    """
    # 1. Receive audio
    try:
        data = await audio.read()
    except Exception as e:
        raise HTTPException(400, f"audio read failed: {e}")

    if not data or len(data) < 100:
        return {"ok": False, "stage": "receive", "error": "empty_audio"}

    # 2. Transcribe with whisper
    model = _get_whisper()
    if not model:
        return {"ok": False, "stage": "stt", "error": "whisper_unavailable"}

    tmp = ROOT / "Logs" / "voice_pipeline_in.wav"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(data)

    try:
        segments, info = model.transcribe(str(tmp), beam_size=1, language="en")
        transcript = " ".join(s.text for s in segments).strip()
    except Exception as e:
        return {"ok": False, "stage": "stt", "error": f"transcribe_failed: {e}"}

    if not transcript:
        return {"ok": False, "stage": "stt", "error": "empty_transcript", "transcript": ""}

    # 3. Dispatch -- chat or task
    try:
        import asyncio
        from dispatcher import dispatch as _dispatch
        result = await asyncio.to_thread(_dispatch, transcript)
    except Exception as e:
        return {"ok": False, "stage": "dispatch", "transcript": transcript, "error": str(e)}

    detail = result.get("detail") or {}
    intent = (detail.get("intent") if isinstance(detail, dict) else None) or ""
    has_action = bool((isinstance(detail, dict) and detail.get("action")) or result.get("action"))

    if has_action:
        mode = "task"
    elif intent in ("greeting", "meta", "unknown", "stop") or not intent:
        mode = "chat"
    else:
        mode = "task"

    reply = result.get("reply", "") or ""

    # 4. Speak the reply out loud
    spoken = False
    if reply:
        try:
            clean = reply.replace("'", "").replace('"', "")
            ps = ("Add-Type -AssemblyName System.Speech; "
                  "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('" + clean + "')")
            subprocess.Popen(["powershell", "-Command", ps],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            spoken = True
        except Exception:
            spoken = False

    # 5. Return full result
    return {
        "ok": bool(result.get("ok")),
        "stage": "complete",
        "transcript": transcript,
        "mode": mode,
        "reply": reply,
        "intent": intent,
        "action": (detail.get("action") if isinstance(detail, dict) else None),
        "target": (detail.get("target") if isinstance(detail, dict) else None),
        "duration_ms": (detail.get("duration_ms") if isinstance(detail, dict) else None),
        "spoken": spoken,
        "detail": detail,
    }
# --- end pipeline ---

# --- Whisper preload (opt) ---
# Load whisper model when this module is imported (server start)
# so first pipeline call is fast.
_get_whisper()
# --- end preload ---


# --- WebSocket voice streaming (Phase 3, added 2026-10-02) ---
from fastapi import WebSocket, WebSocketDisconnect
import base64 as _b64

@router.websocket("/ws")
async def voice_ws(websocket: WebSocket):
    """
    Bidirectional voice channel.

    Client -> Server messages (JSON):
      {"type":"text", "data":"open notepad"}   -> direct text command
      {"type":"audio","data":"<base64 wav>"}   -> transcribe + dispatch
      {"type":"ping"}                          -> heartbeat

    Server -> Client messages (JSON):
      {"type":"ready"}                         -> on connect
      {"type":"result", "transcript":..., "mode":..., "reply":...,
       "action":..., "target":..., "spoken":...}
      {"type":"pong"}
      {"type":"error","error":"..."}
    """
    await websocket.accept()
    try:
        await websocket.send_json({"type": "ready", "service": "royal_jarvis_voice"})
        while True:
            msg = await websocket.receive_json()
            mtype = msg.get("type")

            if mtype == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # --- Direct text command ---
            if mtype == "text":
                text = (msg.get("data") or "").strip()
                if not text:
                    await websocket.send_json({"type": "error", "error": "empty_text"})
                    continue
                # dispatch off the event loop
                try:
                    from dispatcher import dispatch as _dispatch
                    result = await asyncio.to_thread(_dispatch, text)
                except Exception as e:
                    await websocket.send_json({"type": "error", "error": str(e)})
                    continue

                detail = result.get("detail") or {}
                has_action = bool(
                    (isinstance(detail, dict) and detail.get("action"))
                    or result.get("action")
                )
                reply = result.get("reply", "") or ""

                # speak reply
                if reply:
                    try:
                        clean = reply.replace("'", "").replace('"', "")
                        ps = ("Add-Type -AssemblyName System.Speech; "
                              "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('" + clean + "')")
                        subprocess.Popen(["powershell", "-Command", ps],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass

                await websocket.send_json({
                    "type": "result",
                    "transcript": text,
                    "mode": "task" if has_action else "chat",
                    "reply": reply,
                    "action": detail.get("action") if isinstance(detail, dict) else None,
                    "target": detail.get("target") if isinstance(detail, dict) else None,
                    "duration_ms": detail.get("duration_ms") if isinstance(detail, dict) else None,
                    "spoken": True,
                })
                continue

            # --- Audio chunk (base64 wav) ---
            if mtype == "audio":
                b64 = msg.get("data") or ""
                if not b64:
                    await websocket.send_json({"type": "error", "error": "empty_audio"})
                    continue
                try:
                    raw = _b64.b64decode(b64)
                except Exception as e:
                    await websocket.send_json({"type": "error", "error": f"b64_decode: {e}"})
                    continue

                model = _get_whisper()
                if not model:
                    await websocket.send_json({"type": "error", "error": "whisper_unavailable"})
                    continue

                tmp = ROOT / "Logs" / "voice_ws_in.wav"
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_bytes(raw)

                try:
                    segments, info = model.transcribe(str(tmp), beam_size=1, language="en")
                    transcript = " ".join(s.text for s in segments).strip()
                except Exception as e:
                    await websocket.send_json({"type": "error", "error": f"transcribe: {e}"})
                    continue

                if not transcript:
                    await websocket.send_json({"type": "error", "error": "empty_transcript"})
                    continue

                try:
                    from dispatcher import dispatch as _dispatch
                    result = await asyncio.to_thread(_dispatch, transcript)
                except Exception as e:
                    await websocket.send_json({"type": "error", "error": str(e)})
                    continue

                detail = result.get("detail") or {}
                has_action = bool(
                    (isinstance(detail, dict) and detail.get("action"))
                    or result.get("action")
                )
                reply = result.get("reply", "") or ""

                if reply:
                    try:
                        clean = reply.replace("'", "").replace('"', "")
                        ps = ("Add-Type -AssemblyName System.Speech; "
                              "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('" + clean + "')")
                        subprocess.Popen(["powershell", "-Command", ps],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass

                await websocket.send_json({
                    "type": "result",
                    "transcript": transcript,
                    "mode": "task" if has_action else "chat",
                    "reply": reply,
                    "action": detail.get("action") if isinstance(detail, dict) else None,
                    "target": detail.get("target") if isinstance(detail, dict) else None,
                    "duration_ms": detail.get("duration_ms") if isinstance(detail, dict) else None,
                    "spoken": True,
                })
                continue

            await websocket.send_json({"type": "error", "error": f"unknown_type: {mtype}"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass
# --- end WebSocket voice ---