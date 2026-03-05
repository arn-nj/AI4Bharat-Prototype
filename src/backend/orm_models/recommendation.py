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


class LLMPrediction(BaseModel):
    """Independent risk + action prediction made by the LLM."""
    risk_level: str                  # high | medium | low
    action: str                      # recycle | repair | refurbish | redeploy | resale
    reasoning: str                   # 1-2 sentence justification
    agrees_with_ml: Optional[bool] = None  # set after ML result is known


class AssessmentResultOut(BaseModel):
    """Combined asset + risk + recommendation returned after form submission."""
    asset_id: str
    risk: "RiskAssessmentOut"  # noqa: F821
    recommendation: RecommendationOut
    llm_prediction: Optional[LLMPrediction] = None


# Resolve forward refs
from .risk import RiskAssessmentOut
AssessmentResultOut.model_rebuild()
