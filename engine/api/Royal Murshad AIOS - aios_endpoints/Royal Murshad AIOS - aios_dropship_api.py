"""
Dropship API â€” endpoints for the dashboard panel.
Mounted by royal_server.py.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["dropship"])

ROOT       = Path(r"D:\\01_PROJECTS\\AIOS")
DROPSHIP   = ROOT / "dropship"
ANALYSIS   = DROPSHIP / "data" / "analysis"
PRODUCTS   = DROPSHIP / "data" / "products"
LOGS       = DROPSHIP / "data" / "logs"
PY         = ROOT / ".venv" / "Scripts" / "python.exe"
SCRAPER    = DROPSHIP / "agents" / "sourcing" / "cj_scraper.py"
ANALYZER   = DROPSHIP / "agents" / "profit_calc" / "batch_analyze.py"


def _safe_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@router.get("/api/dropship/products")
def dropship_products():
    """Return all analyzed products, sorted by score (highest first)."""
    if not ANALYSIS.exists():
        return {"ok": True, "count": 0, "products": []}

    products = []
    for f in ANALYSIS.glob("*.json"):
        d = _safe_json(f)
        if not d:
            continue
        # Skip non-product entries
        if "profit" not in d or "score" not in d:
            continue
        products.append(d)

    products.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {
        "ok": True,
        "count": len(products),
        "products": products,
    }


@router.get("/api/dropship/raw-products")
def dropship_raw_products():
    """Return all raw sourced products (before analysis)."""
    if not PRODUCTS.exists():
        return {"ok": True, "count": 0, "products": []}

    products = []
    for f in PRODUCTS.glob("cj_*.json"):
        d = _safe_json(f)
        if d:
            products.append(d)

    return {"ok": True, "count": len(products), "products": products}


def _run_script(script: Path, timeout: int = 180) -> dict:
    """Run a Python script and return ok/error with stdout/stderr."""
    if not script.exists():
        return {"ok": False, "error": f"script not found: {script}"}
    if not PY.exists():
        return {"ok": False, "error": f"python not found: {PY}"}

    try:
        result = subprocess.run(
            [str(PY), str(script)],
            cwd=str(DROPSHIP),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": (result.stdout or "")[-4000:],
            "stderr": (result.stderr or "")[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "script timed out"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/dropship/scrape")
def dropship_scrape():
    """Run the CJ scraper. Returns count of products saved."""
    result = _run_script(SCRAPER, timeout=120)
    if not result.get("ok"):
        raise HTTPException(500, result)

    # Count how many CJ products exist now
    count = len(list(PRODUCTS.glob("cj_*.json"))) if PRODUCTS.exists() else 0

    return {
        "ok": True,
        "count": count,
        "stdout_tail": result.get("stdout", "")[-500:],
    }


@router.post("/api/dropship/analyze")
def dropship_analyze():
    """Run the batch analyzer. Returns count of analyses saved."""
    result = _run_script(ANALYZER, timeout=300)
    if not result.get("ok"):
        raise HTTPException(500, result)

    count = len(list(ANALYSIS.glob("*.json"))) if ANALYSIS.exists() else 0

    return {
        "ok": True,
        "count": count,
        "stdout_tail": result.get("stdout", "")[-500:],
    }


@router.post("/api/dropship/pipeline")
def dropship_pipeline():
    """Run scraper, then analyzer. Full pipeline."""
    # Scrape
    scrape_result = _run_script(SCRAPER, timeout=120)
    if not scrape_result.get("ok"):
        raise HTTPException(500, {"stage": "scrape", **scrape_result})

    scraped = len(list(PRODUCTS.glob("cj_*.json"))) if PRODUCTS.exists() else 0

    # Analyze
    analyze_result = _run_script(ANALYZER, timeout=300)
    if not analyze_result.get("ok"):
        raise HTTPException(500, {"stage": "analyze", **analyze_result})

    analyzed = len(list(ANALYSIS.glob("*.json"))) if ANALYSIS.exists() else 0

    return {
        "ok": True,
        "scraped": scraped,
        "analyzed": analyzed,
    }


@router.get("/api/dropship/stats")
def dropship_stats():
    """Summary stats for the dashboard."""
    if not ANALYSIS.exists():
        return {"ok": True, "total": 0, "strong_buy": 0, "good": 0, "maybe": 0, "skip": 0}

    strong = good = maybe = skip = 0
    total_profit = 0.0
    total_margin = 0.0
    n = 0

    for f in ANALYSIS.glob("*.json"):
        d = _safe_json(f)
        if not d or "score" not in d:
            continue
        n += 1
        verdict = d.get("verdict", "SKIP")
        if verdict == "STRONG BUY":
            strong += 1
        elif verdict == "GOOD":
            good += 1
        elif verdict == "MAYBE":
            maybe += 1
        else:
            skip += 1
        p = d.get("profit", {})
        total_profit += p.get("gross_profit", 0)
        total_margin += p.get("margin_pct", 0)

    return {
        "ok": True,
        "total": n,
        "strong_buy": strong,
        "good": good,
        "maybe": maybe,
        "skip": skip,
        "avg_profit": round(total_profit / n, 2) if n else 0,
        "avg_margin": round(total_margin / n, 1) if n else 0,
    }