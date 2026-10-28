"""CookieGuard + Wallet endpoints. Loaded by royal_server.py via exec()."""
import uuid as _dw_uuid
import os as _dw_os
from pathlib import Path as _P
import json as _dw_json
import base64 as _dw_b64
import hashlib as _dw_hash
import subprocess as _dw_sub
import sys as _dw_sys
from datetime import datetime as _dw_dt, timezone as _dw_tz

def _dw_now():
    return _dw_dt.now(_dw_tz.utc).isoformat().replace("+00:00","Z")

_VW_CRYPTO = None
try:
    _dw_sys.path.insert(0, str(_DRAGON_ROOT))
    import aios_vault_crypto as _vw_crypto_mod
    _VW_CRYPTO = _vw_crypto_mod
except Exception:
    pass

def _vw_encrypt(text):
    if _VW_CRYPTO and hasattr(_VW_CRYPTO, "encrypt"):
        try: return _VW_CRYPTO.encrypt(text)
        except Exception: pass
    return "b64:" + _dw_b64.b64encode(text.encode()).decode()

def _vw_decrypt(token):
    if token.startswith("b64:"):
        return _dw_b64.b64decode(token[4:]).decode()
    if _VW_CRYPTO and hasattr(_VW_CRYPTO, "decrypt"):
        try: return _VW_CRYPTO.decrypt(token)
        except Exception: pass
    return token

_LOCAL = _dw_os.environ.get("LOCALAPPDATA", r"C:\Users\royal\AppData\Local")
_COOKIE_PATHS = {
    "chrome_cookies":        _dw_os.path.join(_LOCAL, "Google", "Chrome", "User Data", "Default", "Network", "Cookies"),
    "chrome_login":          _dw_os.path.join(_LOCAL, "Google", "Chrome", "User Data", "Default", "Login Data"),
    "chrome_ext_cookies":    _dw_os.path.join(_LOCAL, "Google", "Chrome", "User Data", "Default", "Storage", "ext", "glic", "66A834677761", "Network", "Cookies"),
    "edge_cookies":          _dw_os.path.join(_LOCAL, "Microsoft", "Edge", "User Data", "Default", "Network", "Cookies"),
    "edge_login":            _dw_os.path.join(_LOCAL, "Microsoft", "Edge", "User Data", "Default", "Login Data"),
    "edge_webview_cookies":  _dw_os.path.join(_LOCAL, "Microsoft", "Edge", "User Data", "OneAuth", "WebView2", "EBWebView", "Default", "Network", "Cookies"),
    "edge_webview_login":    _dw_os.path.join(_LOCAL, "Microsoft", "Edge", "User Data", "OneAuth", "WebView2", "EBWebView", "Default", "Login Data"),
    "growth_profile":        str(_DRAGON_ROOT / ".." / "Everything" / "01_ROYAL_JARVIS" / "11_TOOLS" / "chrome_growth_profile" / "Default" / "Network" / "Cookies"),
}

@app.get("/api/cookieguard/stats")
def _cg_stats():
    d = _dragon_load_json("cookieguard_store.json", {"events": [], "sessions": [], "alerts": []})
    return {"ok": True, "events": len(d.get("events", [])),
            "sessions": len(d.get("sessions", [])),
            "alerts": len(d.get("alerts", [])),
            "monitored_paths": len(_COOKIE_PATHS)}

@app.get("/api/cookieguard/paths")
def _cg_paths():
    items = []
    for name, p in _COOKIE_PATHS.items():
        from pathlib import Path as _P
        pp = _P(p) if not isinstance(p, _P) else p
        items.append({"name": name, "path": str(pp), "exists": pp.exists(),
                      "size": pp.stat().st_size if pp.exists() else 0})
    return {"ok": True, "items": items, "total": len(items)}

@app.post("/api/cookieguard/scan")
def _cg_scan():
    d = _dragon_load_json("cookieguard_store.json", {"events": [], "sessions": [], "alerts": []})
    snapshots = []
    for name, p in _COOKIE_PATHS.items():
        pp = _P(p) if not isinstance(p, _P) else p
        if pp.exists():
            st = pp.stat()
            snapshots.append({"name": name, "path": str(pp),
                              "size": st.st_size, "mtime": st.st_mtime,
                              "sha": _dw_hash.sha256(str(st.st_size).encode()).hexdigest()[:16]})
    d.setdefault("events", []).append({"id": _dw_uuid.uuid4().hex[:8],
                                        "action": "scan", "ts": _dw_now(),
                                        "snapshots": snapshots})
    _dragon_save_json("cookieguard_store.json", d)
    return {"ok": True, "snapshots": snapshots, "count": len(snapshots)}

@app.get("/api/cookieguard/processes")
def _cg_processes():
    results = []
    try:
        r = _dw_sub.run(["powershell", "-Command",
                         'Get-Process | Where-Object { $_.ProcessName -match "chrome|edge|firefox" } | Select-Object ProcessName, Id | ConvertTo-Json'],
                        capture_output=True, text=True, timeout=15)
        if r.stdout.strip():
            import json as _j
            data = _j.loads(r.stdout)
            if isinstance(data, dict): data = [data]
            results = data[:30]
    except Exception as e:
        results = [{"error": str(e)[:80]}]
    return {"ok": True, "items": results, "total": len(results)}

@app.get("/api/cookieguard/sessions")
def _cg_sessions():
    d = _dragon_load_json("cookieguard_store.json", {"events": [], "sessions": [], "alerts": []})
    return {"ok": True, "items": d.get("sessions", []), "total": len(d.get("sessions", []))}

@app.post("/api/cookieguard/sessions")
def _cg_session_add(body: dict = {}):
    d = _dragon_load_json("cookieguard_store.json", {"events": [], "sessions": [], "alerts": []})
    iid = _dw_uuid.uuid4().hex[:8]
    sess = {"id": iid, "platform": body.get("platform") or "Unknown",
            "device": body.get("device") or "Current",
            "location": body.get("location") or "Home",
            "notes": body.get("notes") or "", "added": _dw_now()}
    d.setdefault("sessions", []).append(sess)
    _dragon_save_json("cookieguard_store.json", d)
    return {"ok": True, "id": iid, "session": sess}

@app.delete("/api/cookieguard/sessions/{sid}")
def _cg_session_del(sid: str):
    d = _dragon_load_json("cookieguard_store.json", {"events": [], "sessions": [], "alerts": []})
    before = len(d.get("sessions", []))
    d["sessions"] = [s for s in d.get("sessions", []) if s.get("id") != sid]
    _dragon_save_json("cookieguard_store.json", d)
    return {"ok": True, "removed": before - len(d["sessions"])}

@app.get("/api/cookieguard/alerts")
def _cg_alerts():
    d = _dragon_load_json("cookieguard_store.json", {"events": [], "sessions": [], "alerts": []})
    items = d.get("alerts", [])
    return {"ok": True, "items": items, "total": len(items)}

@app.post("/api/cookieguard/alerts")
def _cg_alert_add(body: dict = {}):
    d = _dragon_load_json("cookieguard_store.json", {"events": [], "sessions": [], "alerts": []})
    iid = _dw_uuid.uuid4().hex[:8]
    alert = {"id": iid, "title": body.get("title") or "Alert",
             "severity": body.get("severity") or "medium",
             "message": body.get("message") or "",
             "resolved": False, "created": _dw_now()}
    d.setdefault("alerts", []).append(alert)
    _dragon_save_json("cookieguard_store.json", d)
    return {"ok": True, "id": iid, "alert": alert}

@app.post("/api/cookieguard/alerts/{aid}/resolve")
def _cg_alert_resolve(aid: str):
    d = _dragon_load_json("cookieguard_store.json", {"events": [], "sessions": [], "alerts": []})
    for a in d.get("alerts", []):
        if a.get("id") == aid:
            a["resolved"] = True
            a["resolved_at"] = _dw_now()
            _dragon_save_json("cookieguard_store.json", d)
            return {"ok": True, "alert": a}
    return {"ok": False, "error": "not found"}

@app.get("/api/cookieguard/breach-check")
def _cg_breach(email: str = ""):
    if not email:
        return {"ok": False, "error": "email required"}
    try:
        sha1 = _dw_hash.sha1(email.strip().lower().encode()).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]
        import urllib.request as _u
        req = _u.Request(f"https://api.pwnedpasswords.com/range/{prefix}",
                         headers={"User-Agent": "ASG-CookieGuard/1.0"})
        with _u.urlopen(req, timeout=10) as r:
            body = r.read().decode()
        hits = [l for l in body.splitlines() if l.startswith(suffix)]
        return {"ok": True, "email_hash_prefix": prefix, "breached": len(hits) > 0, "count": len(hits)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:100]}

@app.get("/api/wallet/stats")
def _w_stats():
    d = _dragon_load_json("wallet_store.json", {"entries": [], "tags": []})
    entries = d.get("entries", [])
    by_type = {}
    for e in entries:
        t = e.get("type", "note")
        by_type[t] = by_type.get(t, 0) + 1
    return {"ok": True, "entries": len(entries), "tags": len(d.get("tags", [])),
            "encrypted": sum(1 for e in entries if e.get("encrypted")), "types": by_type}

@app.get("/api/wallet/entries")
def _w_list():
    d = _dragon_load_json("wallet_store.json", {"entries": [], "tags": []})
    items = []
    for e in d.get("entries", []):
        safe = {k: v for k, v in e.items() if k != "content"}
        safe["content_preview"] = "(encrypted)" if e.get("encrypted") else (e.get("content", "")[:80])
        items.append(safe)
    return {"ok": True, "items": items, "total": len(items)}

@app.post("/api/wallet/entries")
def _w_add(body: dict = {}):
    d = _dragon_load_json("wallet_store.json", {"entries": [], "tags": []})
    iid = _dw_uuid.uuid4().hex[:8]
    raw = body.get("content") or ""
    enc = bool(body.get("encrypt", False))
    entry = {"id": iid, "title": body.get("title") or f"Entry_{iid}",
             "type": body.get("type") or "note",
             "tags": [t.strip() for t in (body.get("tags") or "").split(",") if t.strip()],
             "content": _vw_encrypt(raw) if enc else raw,
             "encrypted": enc, "created": _dw_now()}
    d.setdefault("entries", []).append(entry)
    known = set(d.get("tags", []))
    known.update(entry["tags"])
    d["tags"] = sorted(known)
    _dragon_save_json("wallet_store.json", d)
    return {"ok": True, "id": iid, "entry": {k: v for k, v in entry.items() if k != "content"}}

@app.get("/api/wallet/entries/{eid}")
def _w_get(eid: str):
    d = _dragon_load_json("wallet_store.json", {"entries": [], "tags": []})
    e = next((x for x in d.get("entries", []) if x.get("id") == eid), None)
    if not e: return {"ok": False, "error": "not found"}
    out = dict(e)
    if e.get("encrypted"): out["content"] = _vw_decrypt(e["content"])
    return {"ok": True, "entry": out}

@app.delete("/api/wallet/entries/{eid}")
def _w_del(eid: str):
    d = _dragon_load_json("wallet_store.json", {"entries": [], "tags": []})
    before = len(d.get("entries", []))
    d["entries"] = [x for x in d.get("entries", []) if x.get("id") != eid]
    _dragon_save_json("wallet_store.json", d)
    return {"ok": True, "removed": before - len(d["entries"])}

@app.get("/api/wallet/search")
def _w_search(q: str = "", tag: str = "", type: str = ""):
    d = _dragon_load_json("wallet_store.json", {"entries": [], "tags": []})
    results = []
    for e in d.get("entries", []):
        if tag and tag not in e.get("tags", []): continue
        if type and e.get("type") != type: continue
        if q:
            body = e.get("content", "")
            if e.get("encrypted"): body = _vw_decrypt(body)
            if q.lower() not in (e.get("title","") + " " + body).lower(): continue
        out = {k: v for k, v in e.items() if k != "content"}
        out["content_preview"] = "(encrypted)" if e.get("encrypted") else body[:80]
        results.append(out)
    return {"ok": True, "items": results, "total": len(results)}

@app.get("/api/wallet/tags")
def _w_tags():
    d = _dragon_load_json("wallet_store.json", {"entries": [], "tags": []})
    return {"ok": True, "items": d.get("tags", []), "total": len(d.get("tags", []))}

print("[defwal] CookieGuard + Wallet endpoints loaded")
