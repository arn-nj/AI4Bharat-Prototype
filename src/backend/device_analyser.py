"""
device_analyser.py — Core analysis orchestrator
================================================

DeviceAnalyser.analyse() drives the full pipeline for a single device:

  Stage 1 — Feature engineering
    Derives computed features the ML model expects but the caller does not
    supply (incident_rate_per_month, critical_incident_ratio,
    battery_degradation_rate, thermal_events_per_month).

  Stage 2 — ML model inference  (skipped when data_completeness < threshold)
    Loads the saved sklearn Pipeline + LabelEncoder from disk once (on first
    call) and caches them for subsequent requests.
    Outputs: risk_label (high/medium/low), class probabilities, confidence band.

  Stage 3 — Policy engine
    Applies deterministic threshold rules independently of the ML result.
    Maps the combined assessment to a lifecycle action.

  Stage 4 — LLM engine
    Calls generate_recommendation_explanation() and scaffold_itsm_task()
    from LLMOpenAI.  Both have built-in 10-second timeout fallbacks.

Path layout (resolved relative to this file):
  ../../model_training/models/risk_label_model.joblib
  ../../model_training/models/model_metadata.json
  ../../llm_engine/llm.py  (imported as module)
"""

from __future__ import annotations

import json
import logging
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

import joblib
import numpy as np
import pandas as pd

# ── Resolve sibling package paths ────────────────────────────────────────────
_BACKEND_DIR    = Path(__file__).parent
_SRC_DIR        = _BACKEND_DIR.parent                  # src/
_LLM_ENGINE_DIR = _SRC_DIR / "llm_engine"
_MODEL_DIR      = _SRC_DIR / "model_training" / "models"

# Add llm_engine to path so we can import LLMOpenAI
if str(_LLM_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_LLM_ENGINE_DIR))

from llm import LLMOpenAI  # noqa: E402  (path-resolved import)

from models import (  # noqa: E402
    AnalysisResult,
    DeviceInput,
    LLMResult,
    MLResult,
    PolicyResult,
)

# ── Constants ─────────────────────────────────────────────────────────────────
_MODEL_PATH        = _MODEL_DIR / "risk_label_model.joblib"
_META_PATH         = _MODEL_DIR / "model_metadata.json"
_DATA_COMPLETENESS_THRESHOLD = 0.6   # below this → policy-only path (Property 3)
_POLICY_VERSION    = "1.0"


# ---------------------------------------------------------------------------
# Module-level model cache (loaded once, reused across requests)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_model() -> tuple:
    """
    Load and cache the sklearn pipeline + label encoder + metadata.
    Returns (pipeline, label_encoder, metadata_dict).
    """
    artifact = joblib.load(_MODEL_PATH)
    pipeline = artifact["pipeline"]
    le       = artifact["label_encoder"]
    with open(_META_PATH) as f:
        meta = json.load(f)
    return pipeline, le, meta


# ---------------------------------------------------------------------------
# DeviceAnalyser
# ---------------------------------------------------------------------------

class DeviceAnalyser:
    """
    Orchestrates the full ML → Policy → LLM analysis pipeline for a device.

    Usage:
        analyser = DeviceAnalyser()
        result   = analyser.analyse(device_input)
    """

    def __init__(self, llm_client: Optional[LLMOpenAI] = None) -> None:
        """
        Parameters
        ----------
        llm_client:
            Optional pre-configured LLMOpenAI instance.  When None a new
            client is created on first use (reads credentials from .env).
        """
        self._llm: Optional[LLMOpenAI] = llm_client

    @property
    def llm(self) -> LLMOpenAI:
        if self._llm is None:
            self._llm = LLMOpenAI()
        return self._llm

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def analyse(self, device: DeviceInput) -> AnalysisResult:
        """
        Run the full analysis pipeline on *device* and return an
        AnalysisResult combining ML, policy, and LLM outputs.

        Parameters
        ----------
        device : DeviceInput
            Validated device data (from the API request body or direct call).

        Returns
        -------
        AnalysisResult
        """
        raw = device.model_dump()

        log.info(
            "[%s] Starting analysis pipeline — device_type=%s  age=%dm  "
            "data_completeness=%.2f",
            device.asset_id, device.device_type,
            device.age_in_months, device.data_completeness,
        )

        # Stage 1 — Derive computed features
        raw = self._derive_features(raw)
        log.debug("[%s] Derived features: incident_rate=%.3f  critical_ratio=%.4f  "
                  "batt_degradation=%.4f  thermal_per_month=%.4f",
                  device.asset_id,
                  raw["incident_rate_per_month"], raw["critical_incident_ratio"],
                  raw["battery_degradation_rate"], raw["thermal_events_per_month"])

        # Stage 2 — ML inference
        ml_result = self._run_ml(raw, device.data_completeness)
        log.info("[%s] ML result — label=%s  score=%.3f  available=%s",
                 device.asset_id, ml_result.risk_label,
                 ml_result.risk_score, ml_result.ml_available)

        # Stage 3 — Policy engine
        policy_result = self._run_policy(raw, ml_result)
        log.info("[%s] Policy result — classification=%s  action=%s  rules=%s",
                 device.asset_id, policy_result.classification,
                 policy_result.recommended_action, policy_result.triggered_rules)

        # Stage 4 — LLM (explanation + ITSM task)
        llm_result = self._run_llm(device, ml_result, policy_result)

        # Confidence score: use ML max_proba when available, else 0.5 (policy-only)
        confidence_score = max(ml_result.p_high, ml_result.p_medium, ml_result.p_low) \
            if ml_result.ml_available else 0.5

        return AnalysisResult(
            asset_id=device.asset_id,
            device_type=device.device_type,
            age_in_months=device.age_in_months,
            department=device.department,
            region=device.region,
            ml_result=ml_result,
            policy_result=policy_result,
            llm_result=llm_result,
            final_action=policy_result.recommended_action,
            confidence_score=round(confidence_score, 4),
        )

    # ------------------------------------------------------------------
    # Stage 1 — Feature engineering
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_features(row: dict) -> dict:
        """
        Compute the four derived numeric features expected by the ML model.
        These mirror the derive_features() helper in model_inference_testing.ipynb.
        """
        age   = max(row.get("age_in_months", 1), 1)
        total = row.get("total_incidents", 0)
        crit  = row.get("critical_incidents", 0)
        bh    = row.get("battery_health_percent", 100)
        therm = row.get("thermal_events_count", 0)

        row["incident_rate_per_month"]  = round(total / max(age / 30 * 3, 1), 3)
        row["critical_incident_ratio"]  = round(crit / total, 4) if total > 0 else 0.0
        row["battery_degradation_rate"] = round((100 - bh) / age, 4)
        row["thermal_events_per_month"] = round(therm / age, 4)
        return row

    # ------------------------------------------------------------------
    # Stage 2 — ML model inference
    # ------------------------------------------------------------------

    @staticmethod
    def _calc_risk_score(row: dict) -> float:
        """
        Weighted risk score formula — identical to the one in
        model_inference_testing.ipynb and train_model.py.

            score = battery(0.25) + thermal(0.20) + SMART(0.20)
                  + incidents(0.20) + age(0.15)
        """
        bs  = (100 - row["battery_health_percent"]) / 100
        ts  = min(row["thermal_events_count"] / 50.0, 1.0)
        ds  = min(row["smart_sectors_reallocated"] / 100.0, 1.0)
        ins = min(row["total_incidents"] / 20.0, 1.0)
        ag  = min(row["age_in_months"] / 72.0, 1.0)
        return round(bs * 0.25 + ts * 0.20 + ds * 0.20 + ins * 0.20 + ag * 0.15, 3)

    @staticmethod
    def _confidence_band(max_proba: float) -> str:
        """Mirror of confidence_band() in model_inference_testing.ipynb."""
        if max_proba >= 0.90:
            return "HIGH"
        if max_proba >= 0.70:
            return "MEDIUM"
        return "LOW"

    def _run_ml(self, row: dict, data_completeness: float) -> MLResult:
        """
        Run the sklearn classifier when data_completeness >= threshold.
        Skip to policy-only path when below threshold (Property 3).
        """
        pipeline, le, meta = _load_model()
        model_version = meta.get("trained_at", "unknown")

        risk_score = self._calc_risk_score(row)

        # Policy-only path
        if data_completeness < _DATA_COMPLETENESS_THRESHOLD:
            return MLResult(
                risk_label=self._label_from_score(risk_score),
                risk_score=risk_score,
                confidence_band="LOW",
                p_high=0.0,
                p_medium=0.0,
                p_low=0.0,
                model_version=model_version,
                ml_available=False,
            )

        cat_feats = meta["categorical_features"]
        num_feats = meta["numeric_features"]
        all_feats = cat_feats + num_feats

        # Build single-row DataFrame in the exact column order the pipeline expects
        record = {f: row.get(f, 0) for f in all_feats}
        df_input = pd.DataFrame([record])
        for col in cat_feats:
            df_input[col] = df_input[col].astype(str)

        pred_encoded = pipeline.predict(df_input)
        pred_probas  = pipeline.predict_proba(df_input)[0]

        risk_label = le.inverse_transform(pred_encoded)[0]
        classes    = le.classes_  # ['high', 'low', 'medium']

        proba_map = {cls: float(pred_probas[i]) for i, cls in enumerate(classes)}
        max_proba = float(max(pred_probas))

        return MLResult(
            risk_label=risk_label,
            risk_score=risk_score,
            confidence_band=self._confidence_band(max_proba),
            p_high=round(proba_map.get("high", 0.0), 4),
            p_medium=round(proba_map.get("medium", 0.0), 4),
            p_low=round(proba_map.get("low", 0.0), 4),
            model_version=model_version,
            ml_available=True,
        )

    @staticmethod
    def _label_from_score(risk_score: float) -> str:
        """Threshold-based fallback label used when ML is skipped."""
        if risk_score >= 0.55:
            return "high"
        if risk_score >= 0.35:
            return "medium"
        return "low"

    # ------------------------------------------------------------------
    # Stage 3 — Policy engine
    # ------------------------------------------------------------------

    def _run_policy(self, row: dict, ml: MLResult) -> PolicyResult:
        """
        Apply the deterministic policy rules from data_requirements.md.

        High risk if:
          (age >= 42 AND total_incidents >= 5)
          OR (thermal_events_count >= 10 OR smart_sectors_reallocated >= 50)

        Medium risk if: partial criteria met
        Low risk if:   criteria not met

        The lifecycle action is then derived from the combined risk signal.
        """
        age     = row.get("age_in_months", 0)
        tickets = row.get("total_incidents", 0)
        thermal = row.get("thermal_events_count", 0)
        smart   = row.get("smart_sectors_reallocated", 0)

        triggered_rules: list[str] = []
        signals: list[str] = []

        # Evaluate each rule
        age_and_tickets = age >= 42 and tickets >= 5
        thermal_breach  = thermal >= 10
        smart_breach    = smart >= 50

        if age_and_tickets:
            triggered_rules.append("age_and_tickets")
            signals.append(f"Age: {age} months (≥42 threshold) + {tickets} incidents (≥5 threshold)")

        if thermal_breach:
            triggered_rules.append("thermal_threshold")
            signals.append(f"Thermal events: {thermal} (≥10 threshold)")

        if smart_breach:
            triggered_rules.append("smart_sectors_threshold")
            signals.append(f"SMART sectors reallocated: {smart} (≥50 threshold)")

        # Classify
        if age_and_tickets or thermal_breach or smart_breach:
            classification = "High"
        elif (age >= 30 and tickets >= 3) or thermal >= 5 or smart >= 25:
            classification = "Medium"
            if not signals:
                signals.append(f"Partial risk indicators: age={age}m, tickets={tickets}, "
                                f"thermal={thermal}, smart_sectors={smart}")
        else:
            classification = "Low"

        # Add ML signal to supporting signals when available
        if ml.ml_available:
            signals.append(
                f"ML model: label={ml.risk_label}, score={ml.risk_score:.3f} "
                f"({ml.confidence_band} confidence)"
            )
        else:
            signals.append("ML model: skipped (data_completeness below threshold)")

        # Map to lifecycle action
        action = self._map_action(
            classification=classification,
            risk_score=ml.risk_score,
            age=age,
            thermal_breach=thermal_breach,
            smart_breach=smart_breach,
            row=row,
        )

        return PolicyResult(
            classification=classification,
            triggered_rules=triggered_rules,
            recommended_action=action,
            supporting_signals=signals,
            policy_version=_POLICY_VERSION,
        )

    @staticmethod
    def _map_action(
        classification: str,
        risk_score: float,
        age: int,
        thermal_breach: bool,
        smart_breach: bool,
        row: dict,
    ) -> str:
        """
        Map risk assessment to a lifecycle action.
        Logic mirrors the Recommendation Service rules in data_requirements.md.

          risk_score >= 0.8 AND age >= 42  → RECYCLE
          risk_score >= 0.7 AND repairable → REPAIR
          risk_score >= 0.5                → REFURBISH
          risk_score < 0.3                 → REDEPLOY
          else                             → RESALE
        """
        repairable = thermal_breach or smart_breach or row.get("overheating_issues") == "True"

        if risk_score >= 0.80 and age >= 42:
            return "RECYCLE"
        if risk_score >= 0.70 and repairable:
            return "REPAIR"
        if risk_score >= 0.50:
            return "REFURBISH"
        if risk_score < 0.30:
            return "REDEPLOY"
        return "RESALE"

    # ------------------------------------------------------------------
    # Stage 4 — LLM engine
    # ------------------------------------------------------------------

    def _run_llm(
        self,
        device: DeviceInput,
        ml: MLResult,
        policy: PolicyResult,
    ) -> LLMResult:
        """
        Call the LLM engine for:
          1. A factual recommendation explanation (≤120 words)
          2. A structured ITSM task (JSON)

        Both methods have built-in 10-second timeout fallbacks in llm.py,
        so this method never raises — it always returns usable content.
        """
        policy_dict = {
            "classification":  policy.classification,
            "triggered_rules": policy.triggered_rules,
        }

        ml_dict = {
            "risk_score":          ml.risk_score,
            "confidence_interval": None,   # not produced by current model version
        } if ml.ml_available else None

        telemetry_dict = {
            "battery_cycles":           device.battery_cycles,
            "smart_sectors_reallocated": device.smart_sectors_reallocated,
            "thermal_events_count":      device.thermal_events_count,
        }

        tickets_dict = {
            "total_incidents":          device.total_incidents,
            "critical_incidents":       device.critical_incidents,
            "avg_resolution_time_hours": device.avg_resolution_time_hours,
        }

        llm_available = True

        # --- Explanation ---
        log.info("[%s] Calling LLM: generate_recommendation_explanation", device.asset_id)
        try:
            explanation = self.llm.generate_recommendation_explanation(
                asset_id=device.asset_id,
                device_type=device.device_type,
                age_months=device.age_in_months,
                department=device.department,
                region=device.region,
                risk_score=ml.risk_score,
                risk_label=ml.risk_label,
                confidence_band=ml.confidence_band,
                recommended_action=policy.recommended_action,
                supporting_signals=policy.supporting_signals,
                policy_result=policy_dict,
                ml_result=ml_dict,
                telemetry=telemetry_dict,
                tickets=tickets_dict,
            )
            log.info("[%s] LLM explanation generated successfully", device.asset_id)
        except Exception as exc:
            # generate_recommendation_explanation already has its own fallback;
            # this outer catch is a safety net
            log.exception(
                "[%s] LLM explanation call failed — using fallback template. Error: %s",
                device.asset_id, exc,
            )
            from prompts import fallback_explanation  # type: ignore[import]
            explanation = fallback_explanation(
                recommended_action=policy.recommended_action,
                risk_score=ml.risk_score,
                age_months=device.age_in_months,
                total_incidents=device.total_incidents,
                risk_label=ml.risk_label,
            )
            llm_available = False

        # --- ITSM task ---
        log.info("[%s] Calling LLM: scaffold_itsm_task", device.asset_id)
        try:
            itsm_task = self.llm.scaffold_itsm_task(
                asset_id=device.asset_id,
                recommended_action=policy.recommended_action,
                rationale=explanation,
                confidence_score=max(ml.p_high, ml.p_medium, ml.p_low),
                device_type=device.device_type,
                department=device.department,
                region=device.region,
                age_months=device.age_in_months,
                compliance_requirements=None,  # extend later via ComplianceService
            )
            log.info("[%s] LLM ITSM task scaffolded successfully", device.asset_id)
        except Exception as exc:
            log.exception(
                "[%s] LLM ITSM task call failed — using fallback template. Error: %s",
                device.asset_id, exc,
            )
            from prompts import fallback_itsm_task  # type: ignore[import]
            itsm_task = fallback_itsm_task(
                asset_id=device.asset_id,
                recommended_action=policy.recommended_action,
                device_type=device.device_type,
                region=device.region,
            )
            llm_available = False

        return LLMResult(
            explanation=explanation,
            itsm_task=itsm_task,
            llm_available=llm_available,
        )
