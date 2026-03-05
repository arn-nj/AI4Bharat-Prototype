"""Approvals router — approval queue + decision processing."""

from __future__ import annotations

from pydantic import BaseModel
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from ..db.database import RecommendationRow, AssetRow, RiskAssessmentRow, get_db
from ..orm_models.audit import ApprovalRequest, AuditEntry, ApprovalDecision
from ..orm_models.recommendation import RecommendationOut
from ..services import approval as approval_svc

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("/queue", response_model=List[dict])
def get_queue(db: Session = Depends(get_db)):
    """Return all recommendations pending approval."""
    recs = db.query(RecommendationRow).all()
    queue = []
    for rec in recs:
        asset = db.query(AssetRow).filter_by(asset_id=rec.asset_id).first()
        if asset and asset.current_state == "review_pending":
            risk = (
                db.query(RiskAssessmentRow)
                .filter_by(asset_id=rec.asset_id)
                .order_by(RiskAssessmentRow.assessed_at.desc())
                .first()
            )
            queue.append({
                "recommendation_id": rec.recommendation_id,
                "asset_id": rec.asset_id,
                "device_type": asset.device_type if asset else "unknown",
                "brand": asset.brand if asset else None,
                "department": asset.department if asset else "unknown",
                "region": asset.region if asset else "unknown",
                "age_months": asset.age_months if asset else 0,
                "action": rec.action,
                "confidence_score": rec.confidence_score,
                "rationale": rec.rationale,
                "policy_version": rec.policy_version,
                "model_version": rec.model_version,
                "created_at": rec.created_at,
                "risk_level": risk.risk_level if risk else None,
                "risk_score": risk.risk_score if risk else None,
                "confidence_band": risk.confidence_band if risk else None,
            })
    return queue


@router.post("/{recommendation_id}/decide", response_model=AuditEntry)
def decide(
    recommendation_id: str,
    payload: ApprovalRequest,
    db: Session = Depends(get_db),
):
    """Approve or reject a recommendation and write an audit trail entry."""
    try:
        return approval_svc.process_decision(
            recommendation_id=recommendation_id,
            decision=payload.decision,
            rationale=payload.rationale,
            actor=payload.actor,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))


class BulkApproveRequest(BaseModel):
    rationale: str = "Bulk approved by manager"
    actor: str = "admin"


@router.post("/approve-all")
def approve_all(payload: BulkApproveRequest, db: Session = Depends(get_db)):
    """Approve every pending recommendation in the queue (skips LLM per-item)."""
    recs = db.query(RecommendationRow).all()
    approved = 0
    failed = 0
    for rec in recs:
        asset = db.query(AssetRow).filter_by(asset_id=rec.asset_id).first()
        if asset and asset.current_state == "review_pending":
            try:
                approval_svc.process_decision(
                    recommendation_id=rec.recommendation_id,
                    decision=ApprovalDecision.APPROVED,
                    rationale=payload.rationale,
                    actor=payload.actor,
                    db=db,
                    generate_llm_impact=False,
                )
                approved += 1
            except Exception:
                failed += 1
    return {"approved": approved, "failed": failed,
            "message": f"Bulk approved {approved} recommendations" + (f" ({failed} failed)" if failed else ".")}
