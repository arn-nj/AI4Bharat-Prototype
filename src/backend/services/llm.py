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
        build_compliance_doc_prompt,
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


# ── Default required fields for compliance docs ──────────────────────────────
_DEFAULT_REQUIRED_FIELDS: Dict[str, list] = {
    "certificate": ["certificate_number", "issuing_authority", "issue_date", "expiry_date", "asset_ids"],
    "invoice": ["invoice_number", "vendor_name", "date", "amount", "asset_ids"],
    "chain_of_custody": ["origin", "handler", "destination", "transfer_date", "asset_ids"],
}


def fleet_narrative(kpis) -> str:
    """Generate a 3-sentence executive summary of fleet health from KPI data."""
    llm = _get_llm()
    if llm is None:
        return ""
    context_data = {
        "total_assets": kpis.total_assets,
        "high_risk": kpis.high_risk,
        "medium_risk": kpis.medium_risk,
        "low_risk": kpis.low_risk,
        "pending_approval": kpis.pending_approval,
        "co2_saved_kg": kpis.co2_saved_kg,
        "lifecycle_actions": kpis.lifecycle_actions,
        "avg_age_months": kpis.avg_age_months,
        "deferred_spend_inr": kpis.deferred_spend_inr,
        "carbon_offset_trees": kpis.carbon_offset_trees,
        "assessed_count": kpis.assessed_count,
    }
    system_msg, user_msg = build_conversational_prompt(
        user_query=(
            "Write a concise 3-sentence executive summary of the current IT fleet health. "
            "Cover: overall risk posture, top recommended actions, and environmental/cost impact. "
            "Do NOT include follow-up queries. Plain prose only — no bullet points or headers."
        ),
        context_data=context_data,
    )
    try:
        text = llm.generic_llm(system_msg, user_msg)
        return text.strip() if text else ""
    except Exception as exc:
        log.warning("fleet_narrative failed (%s)", exc)
        return ""


def analyze_compliance_doc(
    *,
    document_type: str,
    region: str,
    asset_id: str,
    file_content: str,
) -> Dict[str, Any]:
    """Analyse a compliance document text and return structured JSON result.

    Returns a dict with keys: summary, extracted_entities, missing_fields,
    verification_status, recommendations.
    Falls back to an error dict if LLM is unavailable.
    """
    llm = _get_llm()
    if llm is None:
        return {
            "summary": "LLM service unavailable — cannot analyse document.",
            "extracted_entities": {},
            "missing_fields": [],
            "verification_status": "INCOMPLETE",
            "recommendations": ["Ensure the LLM service is configured and retry."],
        }

    required_fields = _DEFAULT_REQUIRED_FIELDS.get(document_type.lower(), ["document_date", "issuer", "asset_id"])
    system_msg, user_msg = build_compliance_doc_prompt(
        document_type=document_type,
        region=region,
        asset_id=asset_id,
        file_content=file_content,
        required_fields=required_fields,
    )
    try:
        raw = llm.generic_llm(system_msg, user_msg)
        if not raw:
            raise ValueError("empty response")
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1])
        return json.loads(raw)
    except Exception as exc:
        log.warning("analyze_compliance_doc failed (%s)", exc)
        return {
            "summary": "Document analysis failed. Please try again.",
            "extracted_entities": {},
            "missing_fields": required_fields,
            "verification_status": "INCOMPLETE",
            "recommendations": ["Retry the analysis or review the document manually."],
        }


def llm_predict(asset) -> Optional[Dict[str, Any]]:
    """Ask the LLM to independently predict risk level + recommended action.

    Returns a dict with keys: risk_level, action, reasoning, or None on failure.
    This is intentionally run BEFORE the recommendation is shown to the user
    so it serves as an independent second opinion.
    """
    llm = _get_llm()
    if llm is None:
        return None

    system_msg = (
        "You are a seasoned IT asset lifecycle risk analyst. "
        "Given hardware attributes and telemetry data for a single device, "
        "independently assess the device and predict its risk level and the "
        "most appropriate lifecycle action.\n\n"
        "Rules:\n"
        "1. Respond with ONLY a valid JSON object — no prose, no markdown fences.\n"
        "2. The JSON must have exactly three fields:\n"
        '   - \"risk_level\"  : \"high\" | \"medium\" | \"low\"\n'
        '   - \"action\"      : \"recycle\" | \"repair\" | \"refurbish\" | \"redeploy\" | \"resale\"\n'
        '   - \"reasoning\"   : string, 1-2 sentences explaining your decision\n'
        "3. Base your decision ONLY on the provided data — do not guess missing fields."
    )

    # Build a concise attribute summary
    lines = [
        f"device_type: {getattr(asset, 'device_type', 'unknown')}",
        f"brand: {getattr(asset, 'brand', None) or 'unknown'}",
        f"age_months: {getattr(asset, 'age_months', 'unknown')}",
        f"department: {getattr(asset, 'department', 'unknown')}",
        f"region: {getattr(asset, 'region', 'unknown')}",
    ]
    for field in ("battery_cycles", "thermal_events_count", "smart_sectors_reallocated",
                  "total_incidents", "critical_incidents"):
        val = getattr(asset, field, None)
        if val is not None:
            lines.append(f"{field}: {val}")

    user_msg = (
        "Assess the following IT asset and respond with ONLY the JSON object:\n\n"
        + "\n".join(lines)
    )

    try:
        raw = llm.generic_llm(system_msg, user_msg)
        if not raw:
            return None
        raw = raw.strip()
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:-1])
        return json.loads(raw)
    except Exception as exc:
        log.warning("llm_predict failed (%s)", exc)
        return None


import re as _re


def _strip_follow_ups(text: str) -> str:
    """Remove any 'Suggested follow-up querie/questions' section the LLM may append."""
    m = _re.search(r'suggested follow[- ]?up\b', text, _re.IGNORECASE)
    return text[:m.start()].rstrip() if m else text


def approval_impact(
    *,
    decision: str,
    action: str,
    asset_id: str,
    device_type: str,
    department: str,
    actor: str,
    rationale: str,
) -> str:
    """Generate a one-paragraph change-log / impact statement for an approval decision."""
    llm = _get_llm()
    if llm is None:
        return ""
    context_data = {
        "decision": decision,
        "action": action,
        "asset_id": asset_id,
        "device_type": device_type,
        "department": department,
        "actor": actor,
        "rationale": rationale,
    }
    system_msg, user_msg = build_conversational_prompt(
        user_query=(
            f"A lifecycle decision has just been recorded. Write a concise 2-sentence "
            f"impact statement suitable for an audit log entry explaining what was decided, "
            f"why it was decided, and what the operational impact will be. "
            f"Plain prose only — no bullet points, headers, or follow-up queries."
        ),
        context_data=context_data,
    )
    try:
        text = llm.generic_llm(system_msg, user_msg)
        return _strip_follow_ups(text.strip()) if text else ""
    except Exception as exc:
        log.warning("approval_impact failed (%s)", exc)
        return ""
