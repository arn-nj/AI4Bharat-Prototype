"""
Approval Workflow Service — state machine transitions + immutable audit trail.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..db.database import AssetRow, RecommendationRow, AuditRow
from ..orm_models.audit import ApprovalDecision, AuditEntry
from ..orm_models.asset import AssetState

ACTION_TO_STATE = {
    "recycle":  AssetState.APPROVED_FOR_RECYCLE,
    "repair":   AssetState.APPROVED_FOR_REPAIR,
    "refurbish": AssetState.APPROVED_FOR_REFURBISH,
    "redeploy": AssetState.APPROVED_FOR_REDEPLOY,
    "resale":   AssetState.APPROVED_FOR_RESALE,
}


def process_decision(
    recommendation_id: str,
    decision: ApprovalDecision,
    rationale: str,
    actor: str,
    db: Session,
    *,
    generate_llm_impact: bool = True,
    override_action: Optional[str] = None,
) -> AuditEntry:
    """Process an approval/rejection and write an immutable audit record."""
    rec = db.query(RecommendationRow).filter_by(recommendation_id=recommendation_id).first()
    if not rec:
        raise ValueError(f"Recommendation {recommendation_id} not found")

    asset = db.query(AssetRow).filter_by(asset_id=rec.asset_id).first()
    if not asset:
        raise ValueError(f"Asset {rec.asset_id} not found")

    previous_state = asset.current_state

    if decision == ApprovalDecision.APPROVED:
        effective_action = override_action if override_action and override_action in ACTION_TO_STATE else rec.action
        if override_action and override_action in ACTION_TO_STATE:
            rec.action = effective_action
        new_state = ACTION_TO_STATE.get(effective_action, AssetState.EXCEPTION).value
        asset.current_state = AssetState.WORKFLOW_IN_PROGRESS.value
    else:
        new_state = AssetState.ACTIVE.value
        asset.current_state = new_state

    asset_snapshot = {
        "asset_id": asset.asset_id,
        "device_type": asset.device_type,
        "age_months": asset.age_months,
        "department": asset.department,
        "region": asset.region,
        "state_at_decision": previous_state,
        "data_completeness": asset.data_completeness,
    }
    rec_snapshot = {
        "recommendation_id": rec.recommendation_id,
        "action": rec.action,
        "confidence_score": rec.confidence_score,
        "rationale": rec.rationale,
        "policy_version": rec.policy_version,
        "model_version": rec.model_version,
    }

    now = datetime.now(timezone.utc).isoformat()

    # Generate LLM impact statement (non-blocking — never delays the commit)
    llm_impact: Optional[str] = None
    if generate_llm_impact:
        try:
            from . import llm as llm_svc  # local import to avoid circular at module level
            llm_impact = llm_svc.approval_impact(
                decision=decision.value,
                action=rec.action,
                asset_id=asset.asset_id,
                device_type=asset.device_type,
                department=asset.department,
                actor=actor,
                rationale=rationale,
            )
        except Exception:
            pass

    audit = AuditRow(
        recommendation_id=recommendation_id,
        asset_id=asset.asset_id,
        action=rec.action,
        decision=decision.value,
        rationale=rationale,
        actor=actor,
        previous_state=previous_state,
        new_state=new_state,
        asset_snapshot_json=json.dumps(asset_snapshot),
        recommendation_snapshot_json=json.dumps(rec_snapshot),
        llm_impact=llm_impact,
        timestamp=now,
    )
    db.add(audit)
    db.commit()

    return AuditEntry(
        audit_id=audit.audit_id,
        recommendation_id=recommendation_id,
        asset_id=asset.asset_id,
        action=rec.action,
        decision=decision.value,
        rationale=rationale,
        actor=actor,
        previous_state=previous_state,
        new_state=new_state,
        asset_snapshot=asset_snapshot,
        recommendation_snapshot=rec_snapshot,
        llm_impact=llm_impact,
        timestamp=now,
    )
