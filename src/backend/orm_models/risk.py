"""Risk assessment Pydantic schemas."""

from __future__ import annotations

import enum
from typing import List, Optional
from pydantic import BaseModel


class ConfidenceBand(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TriggeredRule(BaseModel):
    rule: str
    description: str
    met: bool


class MLScores(BaseModel):
    """ML model probability output (present when data_completeness >= 0.6)."""
    ml_risk_label: str               # high / medium / low
    p_high: float
    p_medium: float
    p_low: float
    model_version: str


class RiskAssessmentOut(BaseModel):
    asset_id: str
    risk_level: RiskLevel
    risk_score: float
    confidence_band: ConfidenceBand
    eval_mode: str   # "policy_only" | "policy_and_ml"
    triggered_rules: List[TriggeredRule]
    ml_scores: Optional[MLScores] = None
    policy_version: str
    assessed_at: str
