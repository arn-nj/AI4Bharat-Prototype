"""
models.py — Pydantic data models for the E-Waste Asset Lifecycle Optimizer API
===============================================================================

DeviceInput   — the body accepted by POST /analyse_device
               and passed directly into DeviceAnalyser.analyse()

AnalysisResult — the structured response returned to the caller,
                containing ML output, policy output, and LLM-generated content
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------

class DeviceInput(BaseModel):
    """
    All data describing a device that needs lifecycle analysis.

    Required fields mirror the features used by the trained ML model
    (see model_metadata.json) plus contextual fields needed by the
    policy engine and LLM prompts.

    Derived features (incident_rate_per_month, critical_incident_ratio,
    battery_degradation_rate, thermal_events_per_month) are computed
    automatically by DeviceAnalyser — callers do NOT need to supply them.
    """

    # ── Identity & context ──────────────────────────────────────────────────
    asset_id: str = Field(
        ...,
        description="Unique identifier for the asset, e.g. 'LAP-2891'",
        examples=["LAP-2891"],
    )
    device_type: str = Field(
        ...,
        description="Type of device: Laptop | Server | Desktop",
        examples=["Laptop"],
    )
    brand: str = Field(
        ...,
        description="Hardware manufacturer, e.g. 'Dell', 'HPE', 'Lenovo'",
        examples=["Dell"],
    )
    department: str = Field(
        ...,
        description="Owning business department",
        examples=["Engineering"],
    )
    region: str = Field(
        ...,
        description="Geographic region of the asset",
        examples=["North America"],
    )
    usage_type: str = Field(
        default="Standard",
        description="Usage classification: Standard | Heavy | Light",
        examples=["Standard"],
    )
    os: str = Field(
        default="Windows 11",
        description="Operating system installed on the device",
        examples=["Windows 11"],
    )

    # ── Age & manufacture ───────────────────────────────────────────────────
    age_in_months: int = Field(
        ...,
        ge=0,
        description="Asset age derived from purchase_date, in whole months",
        examples=[48],
    )
    model_year: int = Field(
        ...,
        ge=2000,
        description="Manufacturing year of the device",
        examples=[2022],
    )

    # ── Battery & hardware health ───────────────────────────────────────────
    battery_health_percent: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Current battery health as a percentage (0–100)",
        examples=[65.0],
    )
    battery_cycles: int = Field(
        ...,
        ge=0,
        description="Number of full charge/discharge cycles completed",
        examples=[450],
    )
    smart_sectors_reallocated: int = Field(
        ...,
        ge=0,
        description="SMART attribute: number of reallocated sectors (drive health signal)",
        examples=[12],
    )
    thermal_events_count: int = Field(
        ...,
        ge=0,
        description="Number of thermal/overheating events recorded in the last 90 days",
        examples=[7],
    )
    overheating_issues: str = Field(
        default="False",
        description="Whether recurring overheating has been flagged: 'True' | 'False'",
        examples=["False"],
    )

    # ── Usage patterns ──────────────────────────────────────────────────────
    daily_usage_hours: float = Field(
        default=8.0,
        ge=0.0,
        le=24.0,
        description="Average daily usage hours",
        examples=[8.0],
    )
    performance_rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Subjective performance rating 1 (very poor) to 5 (excellent)",
        examples=[3],
    )

    # ── Support tickets (90-day window) ────────────────────────────────────
    total_incidents: int = Field(
        ...,
        ge=0,
        description="Total support tickets raised in the last 90 days",
        examples=[8],
    )
    critical_incidents: int = Field(
        default=0,
        ge=0,
        description="Number of P1/critical-severity incidents in the 90-day window",
        examples=[1],
    )
    high_incidents: int = Field(
        default=0,
        ge=0,
        description="Number of high-severity incidents in the 90-day window",
        examples=[2],
    )
    medium_incidents: int = Field(
        default=0,
        ge=0,
        description="Number of medium-severity incidents in the 90-day window",
        examples=[3],
    )
    low_incidents: int = Field(
        default=0,
        ge=0,
        description="Number of low-severity incidents in the 90-day window",
        examples=[2],
    )
    avg_resolution_time_hours: float = Field(
        default=24.0,
        ge=0.0,
        description="Average time to resolve incidents in hours",
        examples=[18.5],
    )

    # ── Data quality ────────────────────────────────────────────────────────
    data_completeness: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Fraction of telemetry fields that are populated (0.0–1.0). "
            "When below the configured threshold the ML model is skipped "
            "and only the policy engine runs."
        ),
        examples=[1.0],
    )

    # ── Validators ──────────────────────────────────────────────────────────
    @field_validator("device_type")
    @classmethod
    def validate_device_type(cls, v: str) -> str:
        allowed = {"Laptop", "Server", "Desktop"}
        if v not in allowed:
            raise ValueError(f"device_type must be one of {allowed}, got '{v}'")
        return v

    @field_validator("overheating_issues")
    @classmethod
    def validate_overheating(cls, v: str) -> str:
        if v not in {"True", "False"}:
            raise ValueError("overheating_issues must be 'True' or 'False'")
        return v


# ---------------------------------------------------------------------------
# Sub-models used inside AnalysisResult
# ---------------------------------------------------------------------------

class MLResult(BaseModel):
    """Output from the trained sklearn risk-label classifier."""
    risk_label: str = Field(description="Predicted risk class: high | medium | low")
    risk_score: float = Field(description="Computed risk score (0.0–1.0) from the formula")
    confidence_band: str = Field(description="HIGH | MEDIUM | LOW confidence (based on max class probability)")
    p_high: float = Field(description="Predicted probability of 'high' class")
    p_medium: float = Field(description="Predicted probability of 'medium' class")
    p_low: float = Field(description="Predicted probability of 'low' class")
    model_version: str = Field(description="Identifier of the model artifact used")
    ml_available: bool = Field(description="False if data_completeness was below threshold — policy-only path taken")


class PolicyResult(BaseModel):
    """Output from the deterministic policy engine."""
    classification: str = Field(description="Policy risk classification: High | Medium | Low")
    triggered_rules: list[str] = Field(description="List of rule identifiers that fired")
    recommended_action: str = Field(
        description="Lifecycle action: RECYCLE | REPAIR | REFURBISH | RESALE | REDEPLOY"
    )
    supporting_signals: list[str] = Field(description="Human-readable list of threshold breaches")
    policy_version: str = Field(default="1.0")


class LLMResult(BaseModel):
    """Output from the LLM engine (explanations + ITSM task)."""
    explanation: str = Field(description="Factual recommendation explanation (≤120 words)")
    itsm_task: dict = Field(description="Structured ITSM task ready for posting")
    llm_available: bool = Field(description="False if LLM timed out and fallback templates were used")


class AnalysisResult(BaseModel):
    """
    Complete analysis result returned by POST /analyse_device.

    Combines ML risk scoring, policy engine classification, and
    LLM-generated explanation + ITSM task into one response.
    """
    asset_id: str
    device_type: str
    age_in_months: int
    department: str
    region: str

    ml_result: MLResult
    policy_result: PolicyResult
    llm_result: LLMResult

    final_action: str = Field(
        description="The definitive lifecycle action recommended (from policy engine)"
    )
    confidence_score: float = Field(
        description="Confidence score for the final action (from ML max_proba or policy fallback)"
    )
