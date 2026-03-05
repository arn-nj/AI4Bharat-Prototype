"""
Recommendation Service — action mapping, LLM rationale generation, and persistence.

Uses structured prompt builders from llm_engine/prompts.py to produce
explanations (build_explanation_prompt) and ITSM tasks (build_itsm_task_prompt)
via Amazon Bedrock, with deterministic fallbacks when LLM is unavailable.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from ..db.database import AssetRow, RecommendationRow, PolicyConfigRow
from ..orm_models.risk import RiskAssessmentOut, RiskLevel, ConfidenceBand
from ..orm_models.recommendation import LifecycleAction, RecommendationOut
from . import llm as llm_svc

log = logging.getLogger(__name__)

# ── Rationale fallback templates ──────────────────────────────

RATIONALE_TEMPLATES = {
    LifecycleAction.RECYCLE: (
        "Device is {age} months old with {incidents} support incidents. "
        "{telemetry_note}Replacement cost is more effective than continued maintenance."
    ),
    LifecycleAction.REPAIR: (
        "Hardware issues detected ({telemetry_note}) but device is serviceable at {age} months. "
        "Targeted repair can extend lifecycle by 12-18 months."
    ),
    LifecycleAction.REFURBISH: (
        "Device shows moderate wear at {age} months. "
        "Refurbishment (battery/disk refresh) can restore productivity for 18-24 more months, "
        "deferring ~$1,200 in replacement costs."
    ),
    LifecycleAction.REDEPLOY: (
        "Device at {age} months is in good condition ({incidents} incidents). "
        "Well-suited for redeployment to a lower-demand role."
    ),
    LifecycleAction.RESALE: (
        "Device at {age} months has low risk and good residual market value. "
        "Certified resale recommended to recover asset value."
    ),
}


def generate_recommendation(
    asset: AssetRow,
    risk: RiskAssessmentOut,
    db: Session,
) -> RecommendationOut:
    """Generate a lifecycle recommendation and persist it."""
    action = _decide_action(asset, risk)
    signals = _build_signals(asset, risk)
    fallback_rationale = _build_template_rationale(action, asset, risk)
    policy = db.query(PolicyConfigRow).first()

    triggered_rule_names = [r.rule for r in risk.triggered_rules if r.met]

    # LLM explanation (rich prompt via llm_engine/prompts.py)
    rationale, model_version = llm_svc.generate_rationale(
        action=action.value,
        device_type=asset.device_type,
        age_months=asset.age_months,
        department=asset.department,
        region=asset.region,
        risk_level=risk.risk_level.value,
        risk_score=risk.risk_score,
        confidence_band=risk.confidence_band.value,
        triggered_rules=triggered_rule_names,
        total_incidents=asset.total_incidents,
        thermal_events_count=asset.thermal_events_count,
        smart_sectors_reallocated=asset.smart_sectors_reallocated,
        battery_cycles=asset.battery_cycles,
        fallback_rationale=fallback_rationale,
    )

    # LLM ITSM task scaffold
    itsm_task = llm_svc.scaffold_itsm_task(
        action=action.value,
        asset_id=asset.asset_id,
        device_type=asset.device_type,
        department=asset.department,
        region=asset.region,
        age_months=asset.age_months,
        confidence_score=risk.risk_score,
        rationale=rationale,
    )

    now = datetime.now(timezone.utc).isoformat()
    row = RecommendationRow(
        asset_id=asset.asset_id,
        action=action.value,
        confidence_score=risk.risk_score,
        rationale=rationale,
        supporting_signals_json=json.dumps(signals),
        itsm_task_json=json.dumps(itsm_task) if itsm_task else None,
        policy_version=policy.policy_version if policy else "v1.0",
        model_version=model_version,
        created_at=now,
    )
    db.add(row)
    asset.current_state = "review_pending"
    db.commit()

    return RecommendationOut(
        recommendation_id=row.recommendation_id,
        asset_id=asset.asset_id,
        action=action,
        confidence_score=risk.risk_score,
        rationale=rationale,
        supporting_signals=signals,
        itsm_task=itsm_task,
        policy_version=row.policy_version,
        model_version=row.model_version,
        created_at=now,
    )


def _decide_action(asset: AssetRow, risk: RiskAssessmentOut) -> LifecycleAction:
    """Map risk level + triggered rules to lifecycle action."""
    if risk.risk_level == RiskLevel.HIGH:
        has_telemetry_issues = any(
            r.met for r in risk.triggered_rules
            if r.rule in ("thermal_events", "smart_sectors")
        )
        age_and_tickets = any(r.met for r in risk.triggered_rules if r.rule == "age_and_tickets")
        if age_and_tickets:
            return LifecycleAction.RECYCLE
        elif has_telemetry_issues:
            return LifecycleAction.REPAIR
        return LifecycleAction.RECYCLE
    elif risk.risk_level == RiskLevel.MEDIUM:
        return LifecycleAction.REFURBISH
    else:  # LOW
        return LifecycleAction.REDEPLOY if asset.age_months < 24 else LifecycleAction.RESALE


def _build_signals(asset: AssetRow, risk: RiskAssessmentOut) -> list[str]:
    policy_age = 42
    policy_tickets = 5
    signals = [f"Age: {asset.age_months} months (threshold: {policy_age})"]
    if asset.total_incidents is not None:
        signals.append(f"Incidents (90d): {asset.total_incidents} (threshold: {policy_tickets})")
    if asset.thermal_events_count is not None:
        signals.append(f"Thermal events: {asset.thermal_events_count} (threshold: 10)")
    if asset.smart_sectors_reallocated is not None:
        signals.append(f"SMART sectors: {asset.smart_sectors_reallocated} (threshold: 50)")
    if asset.battery_cycles is not None:
        wear = "high" if asset.battery_cycles > 800 else "moderate" if asset.battery_cycles > 400 else "low"
        signals.append(f"Battery cycles: {asset.battery_cycles} ({wear} wear)")
    if risk.ml_scores:
        signals.append(
            f"ML model: {risk.ml_scores.ml_risk_label} "
            f"(p_high={risk.ml_scores.p_high:.2f}, p_medium={risk.ml_scores.p_medium:.2f}, "
            f"p_low={risk.ml_scores.p_low:.2f})"
        )
    signals.append(f"Eval mode: {risk.eval_mode}")
    signals.append(f"Confidence: {risk.confidence_band.value}")
    return signals


def _build_template_rationale(action: LifecycleAction, asset: AssetRow, risk: RiskAssessmentOut) -> str:
    parts = []
    if asset.thermal_events_count and asset.thermal_events_count > 0:
        parts.append(f"thermal events: {asset.thermal_events_count}")
    if asset.smart_sectors_reallocated and asset.smart_sectors_reallocated > 0:
        parts.append(f"SMART sectors: {asset.smart_sectors_reallocated}")
    if asset.battery_cycles and asset.battery_cycles > 800:
        parts.append(f"battery cycles: {asset.battery_cycles}")
    telemetry_note = ", ".join(parts) + ". " if parts else ""
    template = RATIONALE_TEMPLATES[action]
    return template.format(
        age=asset.age_months,
        incidents=asset.total_incidents or 0,
        telemetry_note=telemetry_note,
    )
