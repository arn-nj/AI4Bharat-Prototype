"""
prompts.py — LLM Prompt Templates for the E-Waste Asset Lifecycle Optimizer
============================================================================

Four prompt builders correspond to the four GenAI use-cases defined in
kiro-specs/data_requirements.md:

  1. build_explanation_prompt       — Requirement 8
     Recommendation Explanation: factual, ≤120 words, hedged language.

  2. build_itsm_task_prompt         — Requirement 9
     ITSM Task Scaffolding: title, description, checklist, JSON output.

  3. build_compliance_doc_prompt    — Requirement 10
     Compliance Document Processing: extract entities, flag gaps.

  4. build_conversational_prompt    — Requirement 11
     Conversational Insights: natural-language query over semantic layer.

Each builder returns a (system_message, user_message) tuple ready to pass
directly into LLMOpenAI.generic_llm() or LLMOpenAI.generic_llm_rest().

Lifecycle action vocabulary (from model_inference_testing.ipynb):
  RECYCLE | REPAIR | REFURBISH | RESALE | REDEPLOY

Risk label vocabulary (from trained classifier):
  high | medium | low

Confidence band vocabulary (from model_inference_testing.ipynb):
  HIGH confidence (max_proba ≥ 0.90)
  MEDIUM confidence (max_proba 0.70–0.89)
  LOW confidence (max_proba < 0.70)
"""

from __future__ import annotations

import json
from typing import Optional


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_ACTION_DESCRIPTIONS = {
    "RECYCLE":   "decommission the asset and certify e-waste disposal",
    "REPAIR":    "raise a maintenance ticket and assess hardware faults",
    "REFURBISH": "clean, upgrade components, and return the asset to the pool",
    "RESALE":    "sell or lease the asset to the secondary market",
    "REDEPLOY":  "reassign the asset to another department or user",
}

_RISK_LABEL_DESCRIPTIONS = {
    "high":   "High — asset shows strong signals of imminent failure or degradation",
    "medium": "Medium — asset has notable wear but remains operational with attention",
    "low":    "Low — asset is in good condition with minor or no issues",
}


def _format_signals(signals: list[str]) -> str:
    """Format supporting signals as a numbered list string."""
    return "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(signals))


# ---------------------------------------------------------------------------
# Prompt 1 — Recommendation Explanation  (Requirement 8)
# ---------------------------------------------------------------------------

def build_explanation_prompt(
    *,
    asset_id: str,
    device_type: str,
    age_months: int,
    department: str,
    region: str,
    risk_score: float,
    risk_label: str,          # high | medium | low  (from ML classifier)
    confidence_band: str,     # HIGH | MEDIUM | LOW confidence
    recommended_action: str,  # RECYCLE | REPAIR | REFURBISH | RESALE | REDEPLOY
    supporting_signals: list[str],
    policy_result: dict,      # {"classification": str, "triggered_rules": list[str]}
    ml_result: Optional[dict] = None,  # {"risk_score": float, "confidence_interval": list[float]}
    telemetry: Optional[dict] = None,  # {"battery_cycles": int, "smart_sectors_reallocated": int, "thermal_events_count": int}
    tickets: Optional[dict] = None,    # {"total_incidents": int, "critical_incidents": int, "avg_resolution_time_hours": float}
) -> tuple[str, str]:
    """
    Build the (system_message, user_message) pair for generating a
    recommendation explanation.

    Design constraints (Requirement 8):
    - Output must be ≤ 120 words
    - Factual: reference only the data signals provided
    - Hedged language when confidence is LOW or MEDIUM
    - Clear connection between signals and the recommended action
    - LLM does NOT make decisions — it explains a decision already made
    """
    action_desc = _ACTION_DESCRIPTIONS.get(recommended_action.upper(), recommended_action)
    risk_desc   = _RISK_LABEL_DESCRIPTIONS.get(risk_label.lower(), risk_label)

    # Build optional telemetry block
    telemetry_block = ""
    if telemetry:
        telemetry_block = (
            f"\nTelemetry readings:\n"
            f"  - Battery cycles          : {telemetry.get('battery_cycles', 'N/A')}\n"
            f"  - SMART sectors reallocated: {telemetry.get('smart_sectors_reallocated', 'N/A')}\n"
            f"  - Thermal events (90 days) : {telemetry.get('thermal_events_count', 'N/A')}"
        )

    # Build optional ticket block
    ticket_block = ""
    if tickets:
        ticket_block = (
            f"\nSupport tickets (90-day window):\n"
            f"  - Total incidents         : {tickets.get('total_incidents', 'N/A')}\n"
            f"  - Critical incidents      : {tickets.get('critical_incidents', 'N/A')}\n"
            f"  - Avg resolution time     : {tickets.get('avg_resolution_time_hours', 'N/A')} hours"
        )

    # Build optional ML result block
    ml_block = ""
    if ml_result:
        ci = ml_result.get("confidence_interval")
        ci_str = f"[{ci[0]:.2f}, {ci[1]:.2f}]" if ci else "N/A"
        ml_block = (
            f"\nML model output:\n"
            f"  - ML risk score           : {ml_result.get('risk_score', risk_score):.3f}\n"
            f"  - Confidence interval     : {ci_str}"
        )
    else:
        ml_block = "\nML model: not run (telemetry completeness below threshold — policy-only evaluation)"

    system_message = (
        "You are a factual assistant that explains IT asset lifecycle decisions "
        "to IT managers. You do NOT make decisions. You only explain decisions "
        "already made by the system using the data signals provided.\n\n"
        "Rules you MUST follow:\n"
        "1. Write exactly one paragraph of plain prose — no bullet points, no headings.\n"
        "2. Stay within 120 words.\n"
        "3. Reference only the data signals provided — do not invent facts.\n"
        "4. When confidence_band is LOW or MEDIUM, use hedged language "
        '   (e.g., "signals suggest", "may indicate", "based on available data").\n'
        "5. When confidence_band is HIGH, write assertively.\n"
        "6. End with a one-sentence summary of the recommended action and its rationale."
    )

    user_message = f"""Generate a factual explanation (≤120 words) for the following asset lifecycle recommendation.

Asset details:
  - Asset ID    : {asset_id}
  - Device type : {device_type}
  - Age         : {age_months} months
  - Department  : {department}
  - Region      : {region}

Risk assessment:
  - Risk label  : {risk_desc}
  - Risk score  : {risk_score:.3f}
  - Confidence  : {confidence_band}

Policy engine result:
  - Classification  : {policy_result.get("classification", "N/A")}
  - Triggered rules : {", ".join(policy_result.get("triggered_rules", [])) or "none"}
{ml_block}
{telemetry_block}
{ticket_block}

Key signals supporting this recommendation:
{_format_signals(supporting_signals)}

Recommended action: {recommended_action.upper()} — {action_desc}

Write the explanation now (≤120 words):"""

    return system_message, user_message


# ---------------------------------------------------------------------------
# Prompt 2 — ITSM Task Scaffolding  (Requirement 9)
# ---------------------------------------------------------------------------

def build_itsm_task_prompt(
    *,
    asset_id: str,
    recommended_action: str,   # RECYCLE | REPAIR | REFURBISH | RESALE | REDEPLOY
    rationale: str,
    confidence_score: float,
    device_type: str,
    department: str,
    region: str,
    age_months: int,
    compliance_requirements: Optional[list[str]] = None,
) -> tuple[str, str]:
    """
    Build the (system_message, user_message) pair for generating an ITSM task.

    Design constraints (Requirement 9):
    - Output must be valid JSON matching the ITSMTaskContent schema
    - Fields: title, description, checklist (list of strings), priority, assigned_team
    - Priority is derived from the recommended action severity
    - Checklist must include compliance steps when compliance_requirements is provided
    - external_ref is always set to the recommendation context (idempotency key)
    """
    compliance_block = ""
    if compliance_requirements:
        compliance_block = (
            "\nCompliance requirements that MUST appear in the checklist:\n"
            + "\n".join(f"  - {r}" for r in compliance_requirements)
        )
    else:
        compliance_block = "\nCompliance requirements: none specified for this region."

    # Priority mapping based on action
    priority_map = {
        "RECYCLE":   "High",
        "REPAIR":    "High",
        "REFURBISH": "Medium",
        "RESALE":    "Medium",
        "REDEPLOY":  "Low",
    }
    suggested_priority = priority_map.get(recommended_action.upper(), "Medium")

    # Team routing suggestion
    team_map = {
        "RECYCLE":   "Asset Disposition",
        "REPAIR":    "Hardware Maintenance",
        "REFURBISH": "Asset Refurbishment",
        "RESALE":    "Asset Disposition",
        "REDEPLOY":  "IT Operations",
    }
    suggested_team = f"{team_map.get(recommended_action.upper(), 'IT Operations')} — {region}"

    system_message = (
        "You are an ITSM workflow assistant. Your job is to generate a structured "
        "task record that an IT operations team can act on immediately.\n\n"
        "Rules you MUST follow:\n"
        "1. Respond with ONLY a valid JSON object — no prose, no markdown fences.\n"
        "2. The JSON must contain exactly these fields:\n"
        '   - "title"        : string, concise and actionable (max 15 words)\n'
        '   - "description"  : string, 2-4 sentences with asset context and background\n'
        '   - "checklist"    : array of strings, each a specific action step\n'
        '   - "priority"     : "High" | "Medium" | "Low"\n'
        '   - "assigned_team": string\n'
        "3. The checklist must always include:\n"
        "   a) Verifying user data backup is complete\n"
        "   b) Updating the asset state in the CMDB upon task completion\n"
        "   c) Any compliance steps listed in the requirements\n"
        "4. Do not include fields not listed above."
    )

    user_message = f"""Generate an ITSM task for the following approved asset lifecycle action.

Asset details:
  - Asset ID    : {asset_id}
  - Device type : {device_type}
  - Age         : {age_months} months
  - Department  : {department}
  - Region      : {region}

Approved action : {recommended_action.upper()} — {_ACTION_DESCRIPTIONS.get(recommended_action.upper(), recommended_action)}
Rationale       : {rationale}
Confidence score: {confidence_score:.2f}
Suggested priority : {suggested_priority}
Suggested team     : {suggested_team}
{compliance_block}

Respond with ONLY the JSON object (no markdown, no extra text):"""

    return system_message, user_message


# ---------------------------------------------------------------------------
# Prompt 3 — Compliance Document Processing  (Requirement 10)
# ---------------------------------------------------------------------------

def build_compliance_doc_prompt(
    *,
    document_type: str,        # certificate | invoice | chain_of_custody
    region: str,
    asset_id: str,
    file_content: str,         # extracted text from the uploaded document
    required_fields: list[str],
    region_requirements: Optional[dict] = None,  # {"India": ["e_waste_certificate", ...]}
) -> tuple[str, str]:
    """
    Build the (system_message, user_message) pair for compliance document
    processing.

    Design constraints (Requirement 10):
    - Extract named entities (dates, vendors, certificate numbers, weights)
    - Flag any required fields that are missing or unclear
    - Summarise key compliance points in plain language
    - Output must be valid JSON
    """
    # Build region requirements block
    region_reqs_block = ""
    if region_requirements and region in region_requirements:
        region_reqs_block = (
            f"\nRegion-specific document requirements for {region}:\n"
            + "\n".join(f"  - {r}" for r in region_requirements[region])
        )
    else:
        region_reqs_block = f"\nNo additional region-specific requirements found for {region}."

    required_fields_str = "\n".join(f"  - {f}" for f in required_fields)

    system_message = (
        "You are a compliance document analyst for IT asset disposition. "
        "You extract structured information from uploaded compliance documents "
        "and verify they meet regional regulatory requirements.\n\n"
        "Rules you MUST follow:\n"
        "1. Respond with ONLY a valid JSON object — no prose, no markdown fences.\n"
        "2. The JSON must contain exactly these fields:\n"
        '   - "summary"              : string, 2-3 sentence plain-language summary\n'
        '   - "extracted_entities"   : object, key-value pairs of found fields\n'
        '   - "missing_fields"       : array of strings — required fields NOT found\n'
        '   - "verification_status"  : "VERIFIED" | "INCOMPLETE" | "REJECTED"\n'
        '   - "recommendations"      : array of strings — corrective actions needed\n'
        "3. verification_status rules:\n"
        '   - "VERIFIED"    : all required_fields are present and legible\n'
        '   - "INCOMPLETE"  : some required_fields missing or unclear\n'
        '   - "REJECTED"    : document type mismatch or content unreadable\n'
        "4. If a field is present but unclear, include it in extracted_entities "
        '   with value "UNCLEAR" and also add it to missing_fields.\n'
        "5. Do not invent data — only extract what is present in the document text."
    )

    user_message = f"""Analyse the following compliance document and extract required information.

Document metadata:
  - Document type : {document_type}
  - Region        : {region}
  - Asset ID      : {asset_id}

Required fields to extract:
{required_fields_str}
{region_reqs_block}

Document content:
---
{file_content}
---

Respond with ONLY the JSON object (no markdown, no extra text):"""

    return system_message, user_message


# ---------------------------------------------------------------------------
# Prompt 4 — Conversational Insights  (Requirement 11)
# ---------------------------------------------------------------------------

# Semantic layer schema — mirrors the data model defined in design.md
_SEMANTIC_LAYER_SCHEMA = {
    "assets": [
        "asset_id", "device_type", "department", "region",
        "current_state", "age_in_months",
    ],
    "recommendations": [
        "recommendation_id", "asset_id", "action",
        "confidence_score", "created_at", "expires_at",
    ],
    "risk_assessments": [
        "asset_id", "risk_score", "risk_label", "confidence_band",
        "policy_classification", "ml_risk_score", "assessment_timestamp",
    ],
    "approval_audits": [
        "audit_id", "recommendation_id", "actor",
        "decision", "timestamp", "rationale",
    ],
}

_AVAILABLE_AGGREGATIONS = [
    "count_by_state",
    "count_by_region",
    "count_by_action",
    "avg_risk_score",
    "avg_age_in_months",
    "recommendations_by_action",
    "approval_rate",
    "override_rate",
]


def build_conversational_prompt(
    *,
    user_query: str,
    semantic_layer_schema: Optional[dict] = None,
    available_aggregations: Optional[list[str]] = None,
    context_data: Optional[dict] = None,  # Optional pre-fetched data to include
) -> tuple[str, str]:
    """
    Build the (system_message, user_message) pair for conversational queries
    over the asset lifecycle semantic layer.

    Design constraints (Requirement 11):
    - Response must answer the user's natural-language question
    - Include data provenance (which tables / fields were used)
    - Suggest 2-3 follow-up queries
    - When context_data is provided, answer directly from it
    - When context_data is absent, generate a structured data query plan
    """
    schema = semantic_layer_schema or _SEMANTIC_LAYER_SCHEMA
    aggregations = available_aggregations or _AVAILABLE_AGGREGATIONS

    schema_str = json.dumps(schema, indent=2)
    aggregations_str = "\n".join(f"  - {a}" for a in aggregations)

    context_block = ""
    if context_data:
        context_block = (
            "\nPre-fetched data relevant to this query:\n"
            f"```json\n{json.dumps(context_data, indent=2, default=str)}\n```\n"
            "Use this data to answer directly. Cite the specific fields used."
        )
    else:
        context_block = (
            "\nNo pre-fetched data provided. "
            "Describe what data you would need to retrieve from the semantic layer "
            "and how you would use it to answer the question."
        )

    system_message = (
        "You are a data analyst assistant for an IT asset lifecycle management system. "
        "You answer questions about asset health, risk assessments, lifecycle decisions, "
        "and operational metrics using the structured semantic layer described below.\n\n"
        "Rules you MUST follow:\n"
        "1. Answer directly and concisely — prioritise facts over filler text.\n"
        "2. Always cite which table(s) and field(s) from the semantic layer you used.\n"
        "3. If the data is insufficient to answer fully, say so clearly and state what "
        "   additional data would be needed.\n"
        "4. End your response with a section labelled 'Suggested follow-up queries:' "
        "   containing exactly 2-3 follow-up questions the user might find useful.\n"
        "5. Do not make up numbers — only use data from the context provided.\n"
        "6. Keep the main answer under 150 words before the follow-up section."
    )

    user_message = f"""Answer the following question about the asset lifecycle management system.

User question: {user_query}

Semantic layer schema (available tables and fields):
```json
{schema_str}
```

Available aggregation operations:
{aggregations_str}
{context_block}

Provide your answer now:"""

    return system_message, user_message


# ---------------------------------------------------------------------------
# Fallback template strings  (used when LLM is unavailable — Requirement 8/9)
# ---------------------------------------------------------------------------

def fallback_explanation(
    *,
    recommended_action: str,
    risk_score: float,
    age_months: int,
    total_incidents: int,
    risk_label: str,
) -> str:
    """
    Template-based explanation used when the LLM service is unavailable or
    times out (> 10 seconds).  Mirrors the fallback pattern in design.md.
    """
    action = recommended_action.upper()
    return (
        f"{action} recommended for this {age_months}-month-old asset based on "
        f"a {risk_label} risk classification (score {risk_score:.2f}) and "
        f"{total_incidents} support incident(s) in the last 90 days. "
        f"Please review the full risk assessment for details."
    )


def fallback_itsm_task(
    *,
    asset_id: str,
    recommended_action: str,
    device_type: str,
    region: str,
) -> dict:
    """
    Minimal ITSM task dict used when the LLM service is unavailable.
    Contains the mandatory fields only.
    """
    action = recommended_action.upper()
    return {
        "title":         f"{action} Asset {asset_id} — {device_type} ({region})",
        "description":   (
            f"Execute {action.lower()} workflow for {device_type} {asset_id} "
            f"in {region} region. Refer to the asset record for full details."
        ),
        "checklist":     [
            "Verify user data backup is complete",
            "Confirm asset details in CMDB",
            "Execute disposition workflow per standard operating procedure",
            "Update asset state to Closed upon completion",
        ],
        "priority":      "High" if action in ("RECYCLE", "REPAIR") else "Medium",
        "assigned_team": f"IT Operations — {region}",
    }
