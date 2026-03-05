"""Recommendation Pydantic schemas."""

from __future__ import annotations

import enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class LifecycleAction(str, enum.Enum):
    REDEPLOY = "redeploy"
    REPAIR = "repair"
    REFURBISH = "refurbish"
    RESALE = "resale"
    RECYCLE = "recycle"


class RecommendationOut(BaseModel):
    model_config = {"protected_namespaces": ()}

    recommendation_id: str
    asset_id: str
    action: LifecycleAction
    confidence_score: float
    rationale: str
    supporting_signals: List[str]
    itsm_task: Optional[Dict[str, Any]] = None
    policy_version: str
    model_version: str
    created_at: str


class AssessmentResultOut(BaseModel):
    """Combined asset + risk + recommendation returned after form submission."""
    asset: "AssetOut"  # noqa: F821
    risk: "RiskAssessmentOut"  # noqa: F821
    recommendation: RecommendationOut


# Resolve forward refs
from .asset import AssetOut
from .risk import RiskAssessmentOut
AssessmentResultOut.model_rebuild()
