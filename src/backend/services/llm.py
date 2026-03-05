"""
LLM Service Bridge — wraps llm_engine/llm.py and prompts.py for use from routers.

Adds the llm_engine directory to sys.path so imports resolve correctly,
then exposes helper functions that the recommendation and AI router services call.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger(__name__)

# ── Resolve llm_engine path ─────────────────────────────────────
_SVC_DIR        = Path(__file__).parent          # src/backend/services/
_SRC_DIR        = _SVC_DIR.parent.parent         # src/
_LLM_ENGINE_DIR = _SRC_DIR / "llm_engine"

if str(_LLM_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(_LLM_ENGINE_DIR))

try:
    from llm import LLMOpenAI           # noqa: E402
    from prompts import (               # noqa: E402
        build_explanation_prompt,
        build_itsm_task_prompt,
        build_conversational_prompt,
        fallback_explanation,
        fallback_itsm_task,
    )
    _LLM_AVAILABLE = True
except Exception as exc:
    log.warning("LLM engine not available (%s) — all calls will use fallbacks", exc)
    _LLM_AVAILABLE = False

_llm: Optional[Any] = None


def _get_llm():
    global _llm
    if _llm is None and _LLM_AVAILABLE:
        _llm = LLMOpenAI()
    return _llm


def generate_rationale(
    *,
    action: str,
    device_type: str,
    age_months: int,
    department: str,
    region: str,
    risk_level: str,
    risk_score: float,
    confidence_band: str,
    triggered_rules: list[str],
    total_incidents: Optional[int] = None,
    thermal_events_count: Optional[int] = None,
    smart_sectors_reallocated: Optional[int] = None,
    battery_cycles: Optional[int] = None,
    fallback_rationale: str = "",
) -> Tuple[str, str]:
    """Generate a rich recommendation explanation via LLM engine.

    Returns (rationale_text, model_version).
    Falls back to fallback_rationale if LLM is unavailable.
    """
    llm = _get_llm()
    if llm is None:
        return fallback_rationale, "rule-based"

    try:
        asset_id = f"{device_type.upper()}-ANALYSIS"

        # Build supporting signals list
        signals: list[str] = [f"Risk level: {risk_level} (score: {risk_score:.2f})"]
        if total_incidents is not None:
            signals.append(f"Total incidents (90d): {total_incidents}")
        if thermal_events_count is not None:
            signals.append(f"Thermal events: {thermal_events_count}")
        if smart_sectors_reallocated is not None:
            signals.append(f"SMART sectors reallocated: {smart_sectors_reallocated}")
        if battery_cycles is not None:
            signals.append(f"Battery cycles: {battery_cycles}")
        for rule in triggered_rules:
            signals.append(f"Triggered rule: {rule}")

        policy_result = {
            "classification": risk_level,
            "triggered_rules": triggered_rules,
        }
        telemetry = None
        if any(v is not None for v in [thermal_events_count, smart_sectors_reallocated, battery_cycles]):
            telemetry = {
                "battery_cycles": battery_cycles,
                "smart_sectors_reallocated": smart_sectors_reallocated,
                "thermal_events_count": thermal_events_count,
            }
        tickets = None
        if total_incidents is not None:
            tickets = {"total_incidents": total_incidents}

        system_msg, user_msg = build_explanation_prompt(
            asset_id=asset_id,
            device_type=device_type,
            age_months=age_months,
            department=department,
            region=region,
            risk_score=risk_score,
            risk_label=risk_level,
            confidence_band=confidence_band,
            recommended_action=action.upper(),
            supporting_signals=signals,
            policy_result=policy_result,
            telemetry=telemetry,
            tickets=tickets,
        )

        text = llm.generic_llm(system_msg, user_msg)
        if not text:
            fb = fallback_rationale or fallback_explanation(
                recommended_action=action.upper(),
                risk_score=risk_score,
                age_months=age_months,
                total_incidents=total_incidents or 0,
                risk_label=risk_level,
            )
            return fb, "qwen3-30b-fallback"
        return text.strip(), "qwen3-30b"

    except Exception as exc:
        log.warning("generate_rationale failed (%s) — using fallback", exc)
        return fallback_rationale, "rule-based"


def scaffold_itsm_task(
    *,
    action: str,
    asset_id: str,
    device_type: str,
    department: str,
    region: str,
    age_months: int,
    confidence_score: float,
    rationale: str,
) -> Optional[Dict[str, Any]]:
    """Generate an ITSM task scaffold as a dict (or None on failure)."""
    llm = _get_llm()
    if llm is None:
        return fallback_itsm_task(
            asset_id=asset_id,
            recommended_action=action.upper(),
            device_type=device_type,
            region=region,
        ) if _LLM_AVAILABLE else None

    try:
        system_msg, user_msg = build_itsm_task_prompt(
            asset_id=asset_id,
            device_type=device_type,
            department=department,
            region=region,
            age_months=age_months,
            recommended_action=action.upper(),
            confidence_score=confidence_score,
            rationale=rationale,
        )
        raw = llm.generic_llm(system_msg, user_msg)
        if not raw:
            return None
        # Try to extract JSON from the response
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1])
        return json.loads(raw)
    except Exception as exc:
        log.warning("scaffold_itsm_task failed (%s)", exc)
        return None


def chat(query: str, context: str = "") -> str:
    """Free-form conversational query for the AI Assistant page."""
    llm = _get_llm()
    if llm is None:
        return "LLM service is currently unavailable. Please check your AWS credentials."

    try:
        context_data = {"fleet_summary": context} if context else None
        system_msg, user_msg = build_conversational_prompt(
            user_query=query,
            context_data=context_data,
        )
        text = llm.generic_llm(system_msg, user_msg)
        return text.strip() if text else "I was unable to generate a response. Please try again."
    except Exception as exc:
        log.warning("chat failed (%s)", exc)
        return "I encountered an error processing your request. Please try again."


def suggest_policy(current_settings: Dict[str, Any]) -> str:
    """Suggest policy threshold adjustments based on current fleet metrics."""
    llm = _get_llm()
    if llm is None:
        return "Policy suggestions require the LLM service to be available."

    try:
        query = (
            "Based on the following fleet configuration, suggest optimal policy "
            f"threshold adjustments: {json.dumps(current_settings, indent=2)}"
        )
        fleet_summary = (
            f"Current policy settings: age threshold={current_settings.get('age_threshold_months')} months, "
            f"ticket threshold={current_settings.get('ticket_threshold')}, "
            f"thermal threshold={current_settings.get('thermal_threshold')}, "
            f"SMART sector threshold={current_settings.get('smart_sector_threshold')}."
        )
        context_data = {"fleet_summary": fleet_summary, "policy_settings": current_settings}
        system_msg, user_msg = build_conversational_prompt(
            user_query=query,
            context_data=context_data,
        )
        text = llm.generic_llm(system_msg, user_msg)
        return text.strip() if text else "No policy suggestions available."
    except Exception as exc:
        log.warning("suggest_policy failed (%s)", exc)
        return "Unable to generate policy suggestions."
