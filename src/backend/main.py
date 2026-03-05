"""
main.py — FastAPI application for the E-Waste Asset Lifecycle Optimizer
========================================================================

Features:
  - Full multi-page workflow (assets, assess, approvals, KPIs, AI, audit)
  - Trained Gradient Boosting ML model (AUC-ROC 0.9962)
  - Rich LLM prompt engineering via Amazon Bedrock (Qwen3 30B)
  - AWS Lambda-compatible via Mangum handler

Routes:
  Assets:    POST/GET /api/assets   GET/DELETE /api/assets/{id}
  Assess:    POST /api/assess/{asset_id}
  Approvals: GET /api/approvals/queue   POST /api/approvals/{id}/decide
  KPIs:      GET /api/kpis
  AI:        POST /api/ai/chat   POST /api/ai/suggest-policy
  Demo:      POST /api/demo/generate   DELETE /api/demo/reset
  Audit:     GET /api/audit
  Health:    GET /api/health   GET /api/model_info

Run locally:
    cd src/backend
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("backend")

# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="E-Waste Asset Lifecycle Optimizer",
    version="2.0.0",
    description=(
        "AI-powered platform for sustainable IT asset lifecycle management. "
        "Combines a trained ML risk model (AUC-ROC 0.9962) with rich LLM prompt "
        "engineering to recommend Recycle, Repair, Refurbish, Redeploy, or Resale."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB init on startup ────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    try:
        from .db.database import init_db, PolicyConfigRow, get_db
        from sqlalchemy.orm import Session
        init_db()
        # Seed default policy config if not present
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            if not db.query(PolicyConfigRow).first():
                db.add(PolicyConfigRow())
                db.commit()
                log.info("Default policy config seeded.")
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        log.warning("DB init skipped during startup (will retry per-request): %s", exc)


# ── Routers ───────────────────────────────────────────────────────────────────

from .routers import assets, assess, approvals, kpis, ai, demo, audit_trail  # noqa: E402

app.include_router(assets.router)
app.include_router(assess.router)
app.include_router(approvals.router)
app.include_router(kpis.router)
app.include_router(ai.router)
app.include_router(demo.router)
app.include_router(audit_trail.router)


# ── Utility endpoints ─────────────────────────────────────────────────────────

_SRC_DIR  = Path(__file__).parent.parent
_META_PATH = _SRC_DIR / "model_training" / "models" / "model_metadata.json"


@app.get("/api/health", tags=["system"])
def health():
    from fastapi.responses import JSONResponse
    db_status = "ok"
    try:
        from .db.database import get_db
        db = next(get_db())
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db.close()
    except Exception as exc:  # noqa: BLE001
        log.warning("Health check DB ping failed: %s", exc)
        db_status = "unavailable"
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "version": "2.0.0", "db": db_status},
    )


@app.get("/api/model_info", tags=["system"])
def model_info():
    try:
        with open(_META_PATH) as f:
            meta = json.load(f)
        return meta
    except FileNotFoundError:
        return {"error": "Model metadata not found", "path": str(_META_PATH)}


# ── AWS Lambda handler ────────────────────────────────────────────────────────
# MUST keep the name `handler` — referenced in template.yaml as:
#   Handler: src.backend.main.handler

handler = Mangum(app, lifespan="off")
