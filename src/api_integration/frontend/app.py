"""
app.py — Streamlit demo UI for the E-Waste Asset Lifecycle Optimizer
=====================================================================

Calls POST /analyse_device on the running FastAPI backend and displays
the ML model output, Policy engine output, and LLM output in clearly
labelled sections.

Usage
-----
1. Start the FastAPI backend:
       cd src/api_integration/backend
       uvicorn main:app --reload --port 8000

2. In a separate terminal, start this UI:
       cd src/api_integration/frontend
       streamlit run app.py

   Optional — point at a non-default backend:
       BACKEND_URL=http://myserver:8000 streamlit run app.py
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Logging — messages appear in the terminal where `streamlit run app.py` runs
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("frontend")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKEND_URL: str = os.environ.get("BACKEND_URL", "http://localhost:8000")
ANALYSE_ENDPOINT: str = f"{BACKEND_URL}/analyse_device"
HEALTH_ENDPOINT: str = f"{BACKEND_URL}/health"

# ---------------------------------------------------------------------------
# Preset scenarios — identical payloads to test_analyse_device.py
# ---------------------------------------------------------------------------

SCENARIOS: list[dict[str, Any]] = [
    {
        "_name": "Brand-new healthy laptop",
        "_expected_action": "REDEPLOY",
        "_expected_risk_score": 0.017,
        "asset_id": "TEST-001",
        "device_type": "Laptop",
        "brand": "Dell",
        "department": "Engineering",
        "region": "North America",
        "usage_type": "Standard",
        "os": "Windows 11",
        "age_in_months": 6,
        "model_year": 2026,
        "battery_health_percent": 98.0,
        "battery_cycles": 40,
        "smart_sectors_reallocated": 0,
        "thermal_events_count": 0,
        "overheating_issues": "False",
        "daily_usage_hours": 8.0,
        "performance_rating": 5,
        "total_incidents": 0,
        "critical_incidents": 0,
        "high_incidents": 0,
        "medium_incidents": 0,
        "low_incidents": 0,
        "avg_resolution_time_hours": 24.0,
        "data_completeness": 1.0,
    },
    {
        "_name": "Young asset, minor wear",
        "_expected_action": "REDEPLOY",
        "_expected_risk_score": 0.115,
        "asset_id": "TEST-002",
        "device_type": "Laptop",
        "brand": "Dell",
        "department": "Engineering",
        "region": "North America",
        "usage_type": "Standard",
        "os": "Windows 11",
        "age_in_months": 18,
        "model_year": 2024,
        "battery_health_percent": 88.0,
        "battery_cycles": 180,
        "smart_sectors_reallocated": 5,
        "thermal_events_count": 2,
        "overheating_issues": "False",
        "daily_usage_hours": 8.0,
        "performance_rating": 4,
        "total_incidents": 3,
        "critical_incidents": 0,
        "high_incidents": 0,
        "medium_incidents": 0,
        "low_incidents": 3,
        "avg_resolution_time_hours": 24.0,
        "data_completeness": 1.0,
    },
    {
        "_name": "Mid-life, average wear",
        "_expected_action": "RESALE",
        "_expected_risk_score": 0.304,
        "asset_id": "TEST-003",
        "device_type": "Laptop",
        "brand": "Dell",
        "department": "Engineering",
        "region": "North America",
        "usage_type": "Standard",
        "os": "Windows 11",
        "age_in_months": 36,
        "model_year": 2023,
        "battery_health_percent": 74.0,
        "battery_cycles": 400,
        "smart_sectors_reallocated": 28,
        "thermal_events_count": 7,
        "overheating_issues": "False",
        "daily_usage_hours": 8.0,
        "performance_rating": 3,
        "total_incidents": 8,
        "critical_incidents": 1,
        "high_incidents": 1,
        "medium_incidents": 2,
        "low_incidents": 4,
        "avg_resolution_time_hours": 24.0,
        "data_completeness": 1.0,
    },
    {
        "_name": "Overheating server, aging",
        "_expected_action": "REFURBISH",
        "_expected_risk_score": 0.584,
        "asset_id": "TEST-004",
        "device_type": "Server",
        "brand": "HPE",
        "department": "Engineering",
        "region": "North America",
        "usage_type": "Standard",
        "os": "Linux",
        "age_in_months": 50,
        "model_year": 2021,
        "battery_health_percent": 60.0,
        "battery_cycles": 600,
        "smart_sectors_reallocated": 60,
        "thermal_events_count": 35,
        "overheating_issues": "True",
        "daily_usage_hours": 8.0,
        "performance_rating": 2,
        "total_incidents": 12,
        "critical_incidents": 2,
        "high_incidents": 2,
        "medium_incidents": 3,
        "low_incidents": 5,
        "avg_resolution_time_hours": 24.0,
        "data_completeness": 1.0,
    },
    {
        "_name": "End-of-life, all signals maxed",
        "_expected_action": "RECYCLE",
        "_expected_risk_score": 0.932,
        "asset_id": "TEST-005",
        "device_type": "Desktop",
        "brand": "Lenovo",
        "department": "Engineering",
        "region": "North America",
        "usage_type": "Standard",
        "os": "Windows 11",
        "age_in_months": 72,
        "model_year": 2019,
        "battery_health_percent": 20.0,
        "battery_cycles": 900,
        "smart_sectors_reallocated": 95,
        "thermal_events_count": 48,
        "overheating_issues": "True",
        "daily_usage_hours": 8.0,
        "performance_rating": 1,
        "total_incidents": 20,
        "critical_incidents": 4,
        "high_incidents": 4,
        "medium_incidents": 6,
        "low_incidents": 6,
        "avg_resolution_time_hours": 24.0,
        "data_completeness": 1.0,
    },
    {
        "_name": "Borderline medium/high (~0.54)",
        "_expected_action": "RESALE",
        "_expected_risk_score": 0.387,
        "asset_id": "TEST-006",
        "device_type": "Laptop",
        "brand": "Dell",
        "department": "Engineering",
        "region": "North America",
        "usage_type": "Standard",
        "os": "Windows 11",
        "age_in_months": 40,
        "model_year": 2022,
        "battery_health_percent": 65.0,
        "battery_cycles": 450,
        "smart_sectors_reallocated": 35,
        "thermal_events_count": 14,
        "overheating_issues": "False",
        "daily_usage_hours": 8.0,
        "performance_rating": 3,
        "total_incidents": 9,
        "critical_incidents": 1,
        "high_incidents": 1,
        "medium_incidents": 2,
        "low_incidents": 5,
        "avg_resolution_time_hours": 24.0,
        "data_completeness": 1.0,
    },
    {
        "_name": "Borderline low/medium (~0.35)",
        "_expected_action": "REDEPLOY",
        "_expected_risk_score": 0.174,
        "asset_id": "TEST-007",
        "device_type": "Laptop",
        "brand": "Dell",
        "department": "Engineering",
        "region": "North America",
        "usage_type": "Standard",
        "os": "Windows 11",
        "age_in_months": 20,
        "model_year": 2024,
        "battery_health_percent": 83.0,
        "battery_cycles": 220,
        "smart_sectors_reallocated": 12,
        "thermal_events_count": 4,
        "overheating_issues": "False",
        "daily_usage_hours": 8.0,
        "performance_rating": 4,
        "total_incidents": 5,
        "critical_incidents": 0,
        "high_incidents": 1,
        "medium_incidents": 1,
        "low_incidents": 3,
        "avg_resolution_time_hours": 24.0,
        "data_completeness": 1.0,
    },
    {
        "_name": "Old but well-maintained",
        "_expected_action": "REDEPLOY",
        "_expected_risk_score": 0.231,
        "asset_id": "TEST-008",
        "device_type": "Laptop",
        "brand": "Dell",
        "department": "Engineering",
        "region": "North America",
        "usage_type": "Standard",
        "os": "Windows 11",
        "age_in_months": 60,
        "model_year": 2020,
        "battery_health_percent": 85.0,
        "battery_cycles": 700,
        "smart_sectors_reallocated": 8,
        "thermal_events_count": 3,
        "overheating_issues": "False",
        "daily_usage_hours": 8.0,
        "performance_rating": 4,
        "total_incidents": 4,
        "critical_incidents": 0,
        "high_incidents": 0,
        "medium_incidents": 1,
        "low_incidents": 3,
        "avg_resolution_time_hours": 24.0,
        "data_completeness": 1.0,
    },
    {
        "_name": "Partial telemetry (completeness=0.45)",
        "_expected_action": "REDEPLOY",
        "_expected_risk_score": 0.231,
        "asset_id": "TEST-009",
        "device_type": "Laptop",
        "brand": "Dell",
        "department": "Engineering",
        "region": "North America",
        "usage_type": "Standard",
        "os": "Windows 11",
        "age_in_months": 30,
        "model_year": 2023,
        "battery_health_percent": 79.0,
        "battery_cycles": 310,
        "smart_sectors_reallocated": 18,
        "thermal_events_count": 5,
        "overheating_issues": "False",
        "daily_usage_hours": 8.0,
        "performance_rating": 3,
        "total_incidents": 6,
        "critical_incidents": 1,
        "high_incidents": 1,
        "medium_incidents": 1,
        "low_incidents": 3,
        "avg_resolution_time_hours": 24.0,
        "data_completeness": 0.45,
    },
    {
        "_name": "High incidents, young device",
        "_expected_action": "RESALE",
        "_expected_risk_score": 0.362,
        "asset_id": "TEST-010",
        "device_type": "Laptop",
        "brand": "Dell",
        "department": "Engineering",
        "region": "North America",
        "usage_type": "Standard",
        "os": "Windows 11",
        "age_in_months": 14,
        "model_year": 2025,
        "battery_health_percent": 90.0,
        "battery_cycles": 150,
        "smart_sectors_reallocated": 55,
        "thermal_events_count": 12,
        "overheating_issues": "True",
        "daily_usage_hours": 8.0,
        "performance_rating": 2,
        "total_incidents": 15,
        "critical_incidents": 3,
        "high_incidents": 3,
        "medium_incidents": 4,
        "low_incidents": 5,
        "avg_resolution_time_hours": 24.0,
        "data_completeness": 1.0,
    },
]

SCENARIO_NAMES: list[str] = [
    f"{i + 1}. {s['_name']}" for i, s in enumerate(SCENARIOS)
]

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

_ACTION_COLOUR: dict[str, str] = {
    "RECYCLE":   "#d32f2f",
    "REPAIR":    "#e65100",
    "REFURBISH": "#f9a825",
    "RESALE":    "#2e7d32",
    "REDEPLOY":  "#1565c0",
}

_RISK_COLOUR: dict[str, str] = {
    "high":   "#d32f2f",
    "medium": "#f9a825",
    "low":    "#2e7d32",
}

_BAND_COLOUR: dict[str, str] = {
    "HIGH":   "#2e7d32",
    "MEDIUM": "#f9a825",
    "LOW":    "#d32f2f",
}


def _action_badge(action: str) -> str:
    colour = _ACTION_COLOUR.get(action, "#555")
    return (
        f'<span style="background:{colour};color:#fff;padding:4px 14px;'
        f'border-radius:4px;font-weight:700;font-size:1.05rem;">{action}</span>'
    )


def _risk_badge(label: str) -> str:
    colour = _RISK_COLOUR.get(label.lower(), "#555")
    return (
        f'<span style="background:{colour};color:#fff;padding:3px 12px;'
        f'border-radius:4px;font-weight:600;">{label.upper()}</span>'
    )


def _band_badge(band: str) -> str:
    colour = _BAND_COLOUR.get(band, "#555")
    return (
        f'<span style="background:{colour};color:#fff;padding:3px 12px;'
        f'border-radius:4px;font-weight:600;">{band}</span>'
    )


# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------

def _build_payload(scenario: dict[str, Any]) -> dict[str, Any]:
    """Strip internal _* keys before sending to the API."""
    return {k: v for k, v in scenario.items() if not k.startswith("_")}


def _check_backend_health() -> bool:
    log.debug("Health check -> %s", HEALTH_ENDPOINT)
    try:
        resp = requests.get(HEALTH_ENDPOINT, timeout=3)
        ok = resp.status_code == 200
        if ok:
            log.info("Backend healthy (HTTP 200)")
        else:
            log.warning("Backend health check returned HTTP %s", resp.status_code)
        return ok
    except Exception as exc:
        log.error("Backend health check failed: %s", exc)
        return False


def _call_analyse(payload: dict[str, Any]) -> tuple[dict | None, str | None]:
    """
    Returns (result_dict, None) on success or (None, error_message) on failure.
    """
    log.info("POST %s  asset_id=%s", ANALYSE_ENDPOINT, payload.get("asset_id"))
    log.debug("Request payload: %s", json.dumps(payload, indent=2))
    try:
        resp = requests.post(ANALYSE_ENDPOINT, json=payload, timeout=60)
        log.debug("Response HTTP %s", resp.status_code)
        if resp.status_code == 200:
            result = resp.json()
            log.info(
                "Analysis complete — final_action=%s  confidence=%.3f  llm_available=%s",
                result.get("final_action"),
                result.get("confidence_score", 0.0),
                result.get("llm_result", {}).get("llm_available"),
            )
            if not result.get("llm_result", {}).get("llm_available", True):
                log.warning(
                    "LLM was unavailable for asset %s — fallback template used. "
                    "Check backend logs for the underlying exception.",
                    payload.get("asset_id"),
                )
            if not result.get("ml_result", {}).get("ml_available", True):
                log.warning(
                    "ML model skipped for asset %s (data_completeness=%.2f < 0.6).",
                    payload.get("asset_id"),
                    payload.get("data_completeness", 0.0),
                )
            return result, None
        error_msg = f"HTTP {resp.status_code}: {resp.text}"
        log.error("Backend returned error: %s", error_msg)
        return None, error_msg
    except requests.exceptions.ConnectionError as exc:
        msg = "Could not connect to the backend. Is the server running?"
        log.error("%s  detail=%s", msg, exc)
        return None, msg
    except requests.exceptions.Timeout:
        msg = "The backend request timed out after 60 seconds."
        log.error(msg)
        return None, msg
    except Exception as exc:
        log.exception("Unexpected error calling backend: %s", exc)
        return None, str(exc)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _render_device_characteristics(scenario: dict[str, Any]) -> None:
    """Display all input fields as two tidy tables side-by-side."""
    import pandas as pd

    st.subheader("Device Characteristics")

    left_rows = [
        ("Asset ID",           scenario["asset_id"]),
        ("Device Type",        scenario["device_type"]),
        ("Brand",              scenario["brand"]),
        ("Department",         scenario["department"]),
        ("Region",             scenario["region"]),
        ("OS",                 scenario["os"]),
        ("Usage Type",         scenario["usage_type"]),
        ("Model Year",         scenario["model_year"]),
        ("Age (months)",       scenario["age_in_months"]),
        ("Daily Usage Hours",  f"{scenario['daily_usage_hours']} h"),
        ("Performance Rating", f"{scenario['performance_rating']} / 5"),
    ]

    right_rows = [
        ("Battery Health",             f"{scenario['battery_health_percent']}%"),
        ("Battery Cycles",             scenario["battery_cycles"]),
        ("SMART Sectors Reallocated",  scenario["smart_sectors_reallocated"]),
        ("Thermal Events (90d)",       scenario["thermal_events_count"]),
        ("Overheating Issues",         scenario["overheating_issues"]),
        ("Total Incidents (90d)",      scenario["total_incidents"]),
        ("Critical Incidents",         scenario["critical_incidents"]),
        ("High Incidents",             scenario["high_incidents"]),
        ("Medium Incidents",           scenario["medium_incidents"]),
        ("Low Incidents",              scenario["low_incidents"]),
        ("Avg Resolution Time",        f"{scenario['avg_resolution_time_hours']} h"),
        ("Data Completeness",          f"{scenario['data_completeness']:.0%}"),
    ]

    df_left  = pd.DataFrame(left_rows,  columns=["Field", "Value"])
    df_right = pd.DataFrame(right_rows, columns=["Field", "Value"])

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("**Identity & Usage**")
        st.dataframe(df_left,  hide_index=True, use_container_width=True)
    with col_r:
        st.markdown("**Hardware Health & Incidents**")
        st.dataframe(df_right, hide_index=True, use_container_width=True)

    if scenario["data_completeness"] < 0.6:
        st.info(
            "Data completeness is below 60%. The ML model will be skipped "
            "and the pipeline will use the Policy engine only."
        )


def _render_ml_result(ml: dict[str, Any]) -> None:
    st.subheader("ML Model Output")

    if not ml.get("ml_available", True):
        st.warning(
            "ML model was skipped because data_completeness < 0.6. "
            "The policy engine ran independently."
        )
        return

    col_label, col_score = st.columns(2)
    col_label.markdown(
        f"**Risk Label**<br>{_risk_badge(ml['risk_label'])}",
        unsafe_allow_html=True,
    )
    col_score.metric("Risk Score", f"{ml['risk_score']:.3f}")

    st.caption(f"Model version (trained at): {ml.get('model_version', 'N/A')}")


def _render_policy_result(policy: dict[str, Any]) -> None:
    st.subheader("Policy Engine Output")

    col_cls, col_action = st.columns(2)
    col_cls.markdown(
        f"**Classification**<br>{_risk_badge(policy['classification'])}",
        unsafe_allow_html=True,
    )
    col_action.markdown(
        f"**Recommended Action**<br>{_action_badge(policy['recommended_action'])}",
        unsafe_allow_html=True,
    )

    st.markdown("**Data used by the Policy Engine**")
    st.info(
        "The policy engine evaluates the following fields from the device input to "
        "classify risk and recommend a lifecycle action:\n\n"
        "- **`age_in_months`** — flags assets older than 42 months that also have ≥ 5 incidents\n"
        "- **`total_incidents`** — combined with age to detect aged high-incident devices\n"
        "- **`thermal_events_count`** — breach at ≥ 10 events triggers a High risk rule\n"
        "- **`smart_sectors_reallocated`** — breach at ≥ 50 sectors triggers a High risk rule\n"
        "- **`overheating_issues`** — used alongside the risk score to qualify the REPAIR action\n"
        "- **`risk_score`** (from ML stage) — drives the lifecycle action mapping:\n"
        "  - ≥ 0.80 AND age ≥ 42 months → **RECYCLE**\n"
        "  - ≥ 0.70 AND device is repairable → **REPAIR**\n"
        "  - ≥ 0.50 → **REFURBISH**\n"
        "  - < 0.30 → **REDEPLOY**\n"
        "  - otherwise → **RESALE**"
    )

    signals = policy.get("supporting_signals", [])
    if signals:
        st.markdown("**Supporting Signals**")
        for sig in signals:
            st.markdown(f"- {sig}")

    st.caption(f"Policy version: {policy.get('policy_version', 'N/A')}")


def _render_llm_result(llm: dict[str, Any]) -> None:
    st.subheader("LLM Engine Output")

    if not llm.get("llm_available", True):
        st.warning("Live LLM was unavailable. A deterministic fallback template was used.")

    st.markdown("**Recommendation Explanation**")
    st.markdown(f"> {llm.get('explanation', 'N/A')}")

    itsm_raw = llm.get("itsm_task")
    if itsm_raw:
        # itsm_task may arrive as a string (JSON) or already parsed dict
        if isinstance(itsm_raw, str):
            try:
                itsm = json.loads(itsm_raw)
            except json.JSONDecodeError:
                itsm = {"raw": itsm_raw}
        else:
            itsm = itsm_raw

        st.markdown("**ITSM Task**")
        col_title, col_prio, col_team = st.columns(3)
        col_title.markdown(f"**Title**  \n{itsm.get('title', 'N/A')}")
        col_prio.markdown(f"**Priority**  \n{itsm.get('priority', 'N/A')}")
        col_team.markdown(f"**Assigned Team**  \n{itsm.get('assigned_team', 'N/A')}")

        st.markdown(f"**Description**  \n{itsm.get('description', 'N/A')}")

        checklist = itsm.get("checklist", [])
        if checklist:
            st.markdown("**Checklist**")
            for item in checklist:
                st.markdown(f"- {item}")


def _render_summary_banner(result: dict[str, Any], scenario: dict[str, Any]) -> None:
    """Full-width banner showing the final action and confidence score."""
    final_action = result.get("final_action", "N/A")
    confidence = result.get("confidence_score", 0.0)
    expected = scenario.get("_expected_action", "")
    match = final_action == expected

    st.markdown("---")
    st.markdown("### Analysis Result")

    col_action, col_conf, col_match = st.columns(3)
    col_action.markdown(
        f"**Final Action**<br>{_action_badge(final_action)}",
        unsafe_allow_html=True,
    )
    col_conf.metric("Confidence Score", f"{confidence:.3f}")
    col_match.markdown(
        f"**Expected Action**  \n`{expected}`  \n"
        + ("Match" if match else "Mismatch — review scenario"),
    )
    st.markdown("---")


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="E-Waste Asset Lifecycle Optimizer",
        page_icon=None,
        layout="wide",
    )

    # ── Header ───────────────────────────────────────────────────────────────
    st.title("E-Waste Asset Lifecycle Optimizer")
    st.markdown(
        "Select one of the 10 preset device scenarios, review its characteristics, "
        "then run the full ML + Policy + LLM pipeline against the live backend."
    )

    # ── Backend status ────────────────────────────────────────────────────────
    backend_ok = _check_backend_health()
    if backend_ok:
        st.success(f"Backend reachable at {BACKEND_URL}")
    else:
        st.error(
            f"Backend not reachable at {BACKEND_URL}. "
            "Start the FastAPI server before running analysis."
        )

    st.divider()

    # ── Scenario selector ─────────────────────────────────────────────────────
    selected_label = st.selectbox(
        "Select a preset scenario",
        options=SCENARIO_NAMES,
        index=0,
    )
    scenario_index = SCENARIO_NAMES.index(selected_label)
    scenario = SCENARIOS[scenario_index]

    st.divider()

    # ── Device characteristics ────────────────────────────────────────────────
    _render_device_characteristics(scenario)

    st.divider()

    # ── Analysis trigger ──────────────────────────────────────────────────────
    run_disabled = not backend_ok
    if st.button("Start Analysis", type="primary", disabled=run_disabled):
        payload = _build_payload(scenario)
        log.info(
            "Starting analysis for scenario '%s' (asset_id=%s)",
            scenario["_name"],
            scenario["asset_id"],
        )
        with st.spinner("Calling backend pipeline (ML + Policy + LLM)..."):
            result, error = _call_analyse(payload)

        if error:
            log.error("Analysis failed for asset %s: %s", scenario["asset_id"], error)
            st.error(f"Analysis failed: {error}")
        else:
            _render_summary_banner(result, scenario)

            tab_ml, tab_policy, tab_llm = st.tabs(
                ["ML Model", "Policy Engine", "LLM Engine"]
            )
            with tab_ml:
                _render_ml_result(result["ml_result"])
            with tab_policy:
                _render_policy_result(result["policy_result"])
            with tab_llm:
                _render_llm_result(result["llm_result"])
    elif run_disabled:
        st.info("Start the FastAPI backend to enable analysis.")


if __name__ == "__main__":
    main()
