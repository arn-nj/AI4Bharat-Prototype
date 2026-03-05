"""
Risk Assessment Service — Policy rules + optional ML model.

Combines policy-driven threshold rules with a trained sklearn Gradient Boosting
model for class probabilities. When data_completeness >= 0.6 the ML model
provides richer signals; policy rules always provide the definitive risk level.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from ..db.database import AssetRow, RiskAssessmentRow, PolicyConfigRow
from ..orm_models.risk import (
    ConfidenceBand, RiskLevel, TriggeredRule, MLScores, RiskAssessmentOut,
)

log = logging.getLogger(__name__)

# ── ML model paths ────────────────────────────────────────────
_SVC_DIR   = Path(__file__).parent          # src/backend/services/
_SRC_DIR   = _SVC_DIR.parent.parent         # src/
_MODEL_DIR = _SRC_DIR / "model_training" / "models"
_MODEL_PATH = _MODEL_DIR / "risk_label_model.joblib"
_META_PATH  = _MODEL_DIR / "model_metadata.json"

_ML_THRESHOLD = 0.6  # data_completeness below this → policy-only


@lru_cache(maxsize=1)
def _load_ml_model():
    """Load the trained sklearn pipeline once and cache it."""
    try:
        import joblib
        artifact = joblib.load(_MODEL_PATH)
        import json as _json
        with open(_META_PATH) as f:
            meta = _json.load(f)
        log.info("ML model loaded — version=%s  AUC-ROC=%s",
                 meta.get("model_version", "unknown"),
                 meta.get("test_metrics", {}).get("auc_roc", "?"))
        return artifact["pipeline"], artifact["label_encoder"], meta
    except Exception as exc:
        log.warning("ML model not available (%s) — policy-only mode", exc)
        return None, None, {}


def _run_ml(asset: AssetRow) -> Optional[MLScores]:
    """Run the trained model if available and data is complete enough."""
    if (asset.data_completeness or 0) < _ML_THRESHOLD:
        return None

    pipeline, le, meta = _load_ml_model()
    if pipeline is None:
        return None

    try:
        import pandas as pd

        age = asset.age_months or 0
        batt_cycles = asset.battery_cycles or 0
        batt_health = asset.battery_health_pct if asset.battery_health_pct is not None else 100.0
        thermal = asset.thermal_events_count or 0
        smart = asset.smart_sectors_reallocated or 0
        incidents = asset.total_incidents or 0
        critical = asset.critical_incidents or 0
        high_i = asset.high_incidents or 0
        medium_i = asset.medium_incidents or 0
        low_i = asset.low_incidents or 0
        avg_res = asset.avg_resolution_time_hours or 24.0

        inc_rate = incidents / max(age, 1)
        crit_ratio = critical / max(incidents, 1)
        batt_deg = (100 - batt_health) / max(age, 1)
        thermal_pm = thermal / max(age, 1)

        # Derive overheating: use stored value if present, else infer from thermal
        if asset.overheating_issues is not None:
            overheating = str(asset.overheating_issues).lower() in ("true", "1", "yes")
        else:
            overheating = thermal > 5

        row = {
            "device_type": asset.device_type,
            "brand": asset.brand or "HP",
            "department": asset.department,
            "region": asset.region,
            "usage_type": asset.usage_type or "Standard",
            "os": asset.os or "Windows 11",
            "overheating_issues": str(overheating),
            "model_year": asset.model_year or (2024 - (age // 12)),
            "age_in_months": age,
            "battery_cycles": batt_cycles,
            "battery_health_percent": batt_health,
            "battery_degradation_rate": batt_deg,
            "smart_sectors_reallocated": smart,
            "thermal_events_count": thermal,
            "thermal_events_per_month": thermal_pm,
            "daily_usage_hours": asset.daily_usage_hours or 8.0,
            "performance_rating": asset.performance_rating or 3,
            "total_incidents": incidents,
            "critical_incidents": critical,
            "high_incidents": high_i,
            "medium_incidents": medium_i,
            "low_incidents": low_i,
            "avg_resolution_time_hours": avg_res,
            "incident_rate_per_month": inc_rate,
            "critical_incident_ratio": crit_ratio,
            "data_completeness": asset.data_completeness or 1.0,
        }
        df = pd.DataFrame([row])
        proba = pipeline.predict_proba(df)[0]
        classes = list(le.classes_)
        proba_map = dict(zip(classes, proba))

        p_high   = float(proba_map.get("high", 0))
        p_medium = float(proba_map.get("medium", 0))
        p_low    = float(proba_map.get("low", 0))
        ml_label = classes[proba.argmax()]

        return MLScores(
            ml_risk_label=ml_label,
            p_high=round(p_high, 4),
            p_medium=round(p_medium, 4),
            p_low=round(p_low, 4),
            model_version=meta.get("model_version", "unknown"),
        )
    except Exception as exc:
        log.warning("ML inference failed (%s) — falling back to policy-only", exc)
        return None


def _get_policy(db: Session) -> PolicyConfigRow:
    row = db.query(PolicyConfigRow).first()
    if row is None:
        return PolicyConfigRow()
    return row


def assess_asset(asset: AssetRow, db: Session) -> RiskAssessmentOut:
    """Run policy engine (+ optional ML) and persist the result."""
    policy = _get_policy(db)

    has_telemetry = any([
        asset.battery_cycles is not None,
        asset.smart_sectors_reallocated is not None,
        asset.thermal_events_count is not None,
    ])
    has_tickets = asset.total_incidents is not None

    # ── Policy rules ─────────────────────────────────────────
    rules: List[TriggeredRule] = []

    age_met    = asset.age_months >= policy.age_threshold_months
    ticket_met = (asset.total_incidents or 0) >= policy.ticket_threshold if has_tickets else False
    rule1_met  = age_met and ticket_met
    rules.append(TriggeredRule(
        rule="age_and_tickets",
        description=(
            f"Age ≥ {policy.age_threshold_months}m ({asset.age_months}) "
            f"AND tickets ≥ {policy.ticket_threshold} ({asset.total_incidents or 'N/A'})"
        ),
        met=rule1_met,
    ))

    thermal_met = (asset.thermal_events_count or 0) >= policy.thermal_threshold if has_telemetry else False
    rules.append(TriggeredRule(
        rule="thermal_events",
        description=(
            f"Thermal ≥ {policy.thermal_threshold} ({asset.thermal_events_count or 'N/A'})"
        ),
        met=thermal_met,
    ))

    smart_met = (asset.smart_sectors_reallocated or 0) >= policy.smart_sector_threshold if has_telemetry else False
    rules.append(TriggeredRule(
        rule="smart_sectors",
        description=(
            f"SMART sectors ≥ {policy.smart_sector_threshold} ({asset.smart_sectors_reallocated or 'N/A'})"
        ),
        met=smart_met,
    ))

    high_criteria    = rule1_met or thermal_met or smart_met
    partial_criteria = age_met or ticket_met

    if high_criteria:
        risk_level = RiskLevel.HIGH
        risk_score = _calc_score(asset, policy, base=0.70)
    elif partial_criteria:
        risk_level = RiskLevel.MEDIUM
        risk_score = _calc_score(asset, policy, base=0.40)
    else:
        risk_level = RiskLevel.LOW
        risk_score = _calc_score(asset, policy, base=0.10)

    # ── Optional ML layer ─────────────────────────────────────
    ml_scores = _run_ml(asset)

    # If ML is available and confident, blend risk_score
    if ml_scores is not None:
        ml_confidence = max(ml_scores.p_high, ml_scores.p_medium, ml_scores.p_low)
        if ml_confidence >= 0.80:
            # Use ML probability to refine score (weighted 60% policy / 40% ML)
            ml_score_val = ml_scores.p_high * 1.0 + ml_scores.p_medium * 0.4 + ml_scores.p_low * 0.0
            risk_score = round(0.60 * risk_score + 0.40 * ml_score_val, 4)
            risk_score = min(risk_score, 1.0)

    # ── Confidence band ───────────────────────────────────────
    eval_mode = "policy_and_ml" if ml_scores else ("policy_and_telemetry" if has_telemetry else "policy_only")
    if ml_scores or (has_telemetry and has_tickets):
        confidence = ConfidenceBand.HIGH
    elif has_telemetry or has_tickets:
        confidence = ConfidenceBand.MEDIUM
    else:
        confidence = ConfidenceBand.LOW

    # ── Persist ───────────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    row = RiskAssessmentRow(
        asset_id=asset.asset_id,
        risk_level=risk_level.value,
        risk_score=round(risk_score, 4),
        confidence_band=confidence.value,
        eval_mode=eval_mode,
        triggered_rules_json=json.dumps([r.model_dump() for r in rules]),
        ml_risk_label=ml_scores.ml_risk_label if ml_scores else None,
        ml_p_high=ml_scores.p_high if ml_scores else None,
        ml_p_medium=ml_scores.p_medium if ml_scores else None,
        ml_p_low=ml_scores.p_low if ml_scores else None,
        policy_version=policy.policy_version,
        assessed_at=now,
    )
    db.add(row)
    db.commit()

    return RiskAssessmentOut(
        asset_id=asset.asset_id,
        risk_level=risk_level,
        risk_score=round(risk_score, 4),
        confidence_band=confidence,
        eval_mode=eval_mode,
        triggered_rules=rules,
        ml_scores=ml_scores,
        policy_version=policy.policy_version,
        assessed_at=now,
    )


def _calc_score(asset: AssetRow, policy: PolicyConfigRow, base: float) -> float:
    """Weighted risk score (0–1) using the 5-factor formula from AI4Bharat."""
    age   = asset.age_months or 0
    batt  = 100.0   # battery_health_percent — not in simplified row, use default
    therm = asset.thermal_events_count or 0
    smart = asset.smart_sectors_reallocated or 0
    inc   = asset.total_incidents or 0

    score = (
        0.25 * (100 - batt) / 100
        + 0.20 * min(therm / 50, 1.0)
        + 0.20 * min(smart / 100, 1.0)
        + 0.20 * min(inc / 20, 1.0)
        + 0.15 * min(age / 72, 1.0)
    )

    # Blend with base from policy classification
    return round(min(0.5 * base + 0.5 * score, 1.0), 4)
