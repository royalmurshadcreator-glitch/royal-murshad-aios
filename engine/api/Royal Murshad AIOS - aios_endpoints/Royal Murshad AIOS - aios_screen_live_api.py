"""ROYAL JARVIS — Live Screen endpoint (capture + OCR for Live Mode)."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pathlib import Path
import sys, io, time, base64

ROOT = Path(r"D:\01_PROJECTS\AIOS")
VISION_DIR = ROOT / "05_MODELS" / "aios_vision"
if str(VISION_DIR) not in sys.path:
    sys.path.insert(0, str(VISION_DIR))

router = APIRouter(prefix="/api/vision", tags=["vision-live"])

_ocr_mod = None
def _get_ocr():
    global _ocr_mod
    if _ocr_mod is None:
        try:
            import aios_screen_ocr as mod
            _ocr_mod = mod
        except Exception as e:
            _ocr_mod = False
            print(f"[vision-live] OCR import failed: {e}")
    return _ocr_mod

@router.get("/screen")
def screen():
    """Capture screen, run OCR, return text + base64 thumbnail."""
    t0 = time.time()
    try:
        from PIL import ImageGrab
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"PIL missing: {e}"}, status_code=500)

    try:
        img = ImageGrab.grab()
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"capture failed: {e}"}, status_code=500)

    # Full-size base64 for the preview (jpeg, quality 60 — small)
    thumb = img.copy()
    thumb.thumbnail((1280, 720))
    buf = io.BytesIO()
    thumb.convert("RGB").save(buf, format="JPEG", quality=60, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()

    # OCR
    text = ""
    ocr_err = None
    mod = _get_ocr()
    if mod and hasattr(mod, "capture_and_ocr"):
        try:
            result = mod.capture_and_ocr(persist=False)
            text = result.get("text", "") if isinstance(result, dict) else ""
        except Exception as e:
            ocr_err = f"ocr error: {e}"
    else:
        ocr_err = "ocr module unavailable"

    return {
        "ok": True,
        "image_b64": b64,
        "text": text[:8000],
        "text_len": len(text),
        "size": list(img.size),
        "elapsed_ms": int((time.time() - t0) * 1000),
        "ocr_error": ocr_err,
    }
