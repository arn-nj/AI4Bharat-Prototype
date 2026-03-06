"""Audit Trail router — immutable log of all approval decisions."""

from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from ..db.database import AuditRow, get_db
from ..orm_models.audit import AuditEntry

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=List[dict])
def list_audit(
    asset_id: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(AuditRow).order_by(AuditRow.timestamp.desc())
    if asset_id:
        q = q.filter_by(asset_id=asset_id)
    if actor:
        q = q.filter_by(actor=actor)
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    result = []
    for r in rows:
        try:
            snap = json.loads(r.asset_snapshot_json or "{}")
        except Exception:
            snap = {}
        result.append({
            "audit_id": r.audit_id,
            "recommendation_id": r.recommendation_id,
            "asset_id": r.asset_id,
            "action": r.action,
            "decision": r.decision,
            "rationale": r.rationale,
            "actor": r.actor,
            "previous_state": r.previous_state,
            "new_state": r.new_state,
            "timestamp": r.timestamp,
            "llm_impact": r.llm_impact,
            "llm_pre_decision_json": r.llm_pre_decision_json,
            "original_action": r.original_action,
            # Fields from asset snapshot for display purposes
            "device_type": snap.get("device_type"),
            "department": snap.get("department"),
            "region": snap.get("region"),
        })
    return result
