"""
main.py — FastAPI application for the E-Waste Asset Lifecycle Optimizer
========================================================================

Endpoints
---------
  POST /analyse_device   — Submit device data; receive ML + policy + LLM result
  GET  /health           — Liveness check
  GET  /model_info       — Returns model metadata (version, metrics, features)

Run locally:
    cd src/api_integration/backend
    uvicorn main:app --reload --port 8000

Then open:
    http://localhost:8000/docs       (Swagger UI)
    http://localhost:8000/redoc      (ReDoc)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# ---------------------------------------------------------------------------
# Logging — configure once so all backend modules share the same format.
# uvicorn also emits to this handler, giving a unified stream in the terminal.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("backend")

# ── Resolve sibling package paths ────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).parent
_SRC_DIR     = _BACKEND_DIR.parent.parent
_META_PATH   = _SRC_DIR / "model_training" / "models" / "model_metadata.json"

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

_STORAGE_DIR = _SRC_DIR / "storage"
if str(_STORAGE_DIR) not in sys.path:
    sys.path.insert(0, str(_STORAGE_DIR))

from device_analyser import DeviceAnalyser  # noqa: E402
from models import AnalysisResult, DeviceInput  # noqa: E402

# S3 storage — optional, enabled when S3_BUCKET_NAME is set
_s3_storage = None
try:
    from s3_storage import S3Storage
    if os.getenv("S3_BUCKET_NAME"):
        _s3_storage = S3Storage()
        log.info("S3 storage enabled — bucket=%s", os.getenv("S3_BUCKET_NAME"))
    else:
        log.info("S3 storage disabled — S3_BUCKET_NAME not set")
except Exception as exc:
    log.warning("S3 storage unavailable: %s", exc)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="E-Waste Asset Lifecycle Optimizer API",
    description=(
        "Analyses IT assets using a trained ML risk classifier, a deterministic "
        "policy engine, and an LLM to generate explanations and ITSM tasks."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single shared analyser instance (model is cached after first load)
_analyser = DeviceAnalyser()

# AWS Lambda handler (used by API Gateway → Lambda integration)
handler = Mangum(app, lifespan="off")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health_check() -> dict:
    """
    Liveness probe.  Returns 200 OK when the service is running.
    """
    return {"status": "ok", "service": "asset-lifecycle-optimizer"}


@app.get("/model_info", tags=["System"])
def model_info() -> dict:
    """
    Returns the metadata of the currently loaded ML model artifact —
    training date, best model name, test metrics, and feature lists.
    """
    if not _META_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model metadata file not found. Ensure the model has been trained.",
        )
    with open(_META_PATH) as f:
        return json.load(f)


@app.post(
    "/analyse_device",
    response_model=AnalysisResult,
    status_code=status.HTTP_200_OK,
    tags=["Analysis"],
    summary="Analyse a device and recommend a lifecycle action",
    response_description=(
        "Full analysis result: ML risk label + probabilities, "
        "policy classification, recommended action, "
        "LLM explanation, and a ready-to-post ITSM task."
    ),
)
def analyse_device(device: DeviceInput) -> AnalysisResult:
    """
    **Pipeline stages executed per request:**

    1. **Feature engineering** — derives `incident_rate_per_month`,
       `critical_incident_ratio`, `battery_degradation_rate`,
       `thermal_events_per_month` from the supplied raw values.

    2. **ML model** — loads the trained sklearn Pipeline from disk (cached),
       predicts risk label (`high` / `medium` / `low`) and class probabilities.
       Skipped when `data_completeness < 0.6` (policy-only path).

    3. **Policy engine** — applies deterministic threshold rules:
       *High* if `(age ≥ 42 AND tickets ≥ 5)` OR `(thermal ≥ 10 OR SMART ≥ 50)`,
       *Medium* if partial criteria, *Low* otherwise.
       Maps the risk level to a lifecycle action
       (RECYCLE / REPAIR / REFURBISH / RESALE / REDEPLOY).

    4. **LLM engine** — generates a factual ≤120-word explanation and a
       structured ITSM task JSON.  Falls back to deterministic templates
       if the LLM service times out (> 10 s) or is unavailable.
    """
    try:
        result = _analyser.analyse(device)
        log.info(
            "Request complete — asset_id=%s  final_action=%s  llm_available=%s",
            device.asset_id,
            result.final_action,
            result.llm_result.llm_available,
        )

        # Persist analysis result to S3 when storage is available
        if _s3_storage:
            try:
                s3_key = _s3_storage.store_analysis_result(
                    asset_id=device.asset_id,
                    result=result.model_dump(),
                )
                log.info("Analysis result stored in S3: %s", s3_key)
            except Exception as s3_exc:
                log.warning("Failed to store result in S3: %s", s3_exc)

        return result
    except FileNotFoundError as exc:
        log.error("Model artifact missing for asset %s: %s", device.asset_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model artifact not found: {exc}. Run train_model.py first.",
        ) from exc
    except Exception as exc:
        log.exception("Unhandled error during analysis for asset %s: %s", device.asset_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {exc}",
        ) from exc
