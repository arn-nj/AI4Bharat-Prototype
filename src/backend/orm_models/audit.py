"""Audit, approval, and KPI Pydantic schemas."""

from __future__ import annotations

import enum
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ApprovalDecision(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalRequest(BaseModel):
    decision: ApprovalDecision
    rationale: str
    actor: str = "demo-user"
    override_action: Optional[str] = None


class AuditEntry(BaseModel):
    audit_id: str
    recommendation_id: str
    asset_id: str
    action: str
    decision: str
    rationale: str
    actor: str
    previous_state: str
    new_state: str
    asset_snapshot: Dict[str, Any]
    recommendation_snapshot: Dict[str, Any]
    timestamp: str
    llm_impact: Optional[str] = None
    llm_pre_decision_json: Optional[str] = None
    original_action: Optional[str] = None


class KPIOut(BaseModel):
    # Core counts
    total_assets: int
    high_risk: int
    medium_risk: int
    low_risk: int
    avg_age_months: float
    assessed_count: int
    pending_approval: int
    approved_count: int
    rejected_count: int
    # Financial (INR)
    deferred_spend_inr: float
    # Action breakdown
    lifecycle_actions: Dict[str, int]
    action_percentages: Dict[str, float]
    # Department breakdown
    departments: Dict[str, int]
    risk_by_department: Dict[str, Dict[str, int]]
    # Environmental impact (strong differentiator)
    co2_saved_kg: float
    landfill_reduction_kg: float
    carbon_offset_trees: int
    material_recovery_pct: float
