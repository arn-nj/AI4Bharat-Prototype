"""
test_analyse_device.py — End-to-end API tests for POST /analyse_device
=======================================================================

Contains the same 10 hand-crafted scenarios defined in
model_inference_testing.ipynb (cell #VSC-a91e3fe1), translated into
API request payloads.

Each scenario is sent to the running FastAPI server and the full
AnalysisResult is printed in a structured, readable format.

Usage
-----
1. Start the API server in a separate terminal:
       cd src/backend
       uvicorn main:app --reload --port 8000

2. Run this file:
       python test_analyse_device.py

   Optional flags:
       --url  http://localhost:8000   (default)
       --stop-on-error                abort after first HTTP error response

Scenarios (mirroring the notebook)
-----------------------------------
 1  Brand-new healthy laptop          → expected REDEPLOY   (score ~0.017)
 2  Young asset, minor wear           → expected REDEPLOY   (score ~0.115)
 3  Mid-life, average wear            → expected RESALE     (score ~0.304)
 4  Overheating server, aging         → expected REFURBISH  (score ~0.584)
 5  End-of-life, all signals maxed    → expected RECYCLE    (score ~0.932)
 6  Borderline medium/high (~0.54)    → expected RESALE     (score ~0.387)
 7  Borderline low/medium (~0.35)     → expected REDEPLOY   (score ~0.174)
 8  Old but well-maintained           → expected REDEPLOY   (score ~0.231)
 9  Partial telemetry (comp=0.45)     → policy-only path    (ML skipped)
10  High incidents, young device      → expected RESALE     (score ~0.362)
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Scenario definitions — exact values from model_inference_testing.ipynb
# The derived features (incident_rate_per_month etc.) are NOT included here;
# DeviceAnalyser computes them server-side.
# ---------------------------------------------------------------------------

SCENARIOS: list[dict[str, Any]] = [
    # ── 1 Brand-new healthy laptop ───────────────────────────────────────────
    {
        "_name": "Brand-new healthy laptop",
        "_expected_zone": "REDEPLOY",
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

    # ── 2 Young asset, minor wear ────────────────────────────────────────────
    {
        "_name": "Young asset, minor wear",
        "_expected_zone": "REDEPLOY",
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

    # ── 3 Mid-life, average wear ─────────────────────────────────────────────
    {
        "_name": "Mid-life, average wear",
        "_expected_zone": "RESALE",
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

    # ── 4 Overheating server, aging ──────────────────────────────────────────
    {
        "_name": "Overheating server, aging",
        "_expected_zone": "REFURBISH",
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

    # ── 5 End-of-life, all signals maxed → RECYCLE ───────────────────────────
    {
        "_name": "End-of-life, all signals maxed",
        "_expected_zone": "RECYCLE",
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

    # ── 6 Borderline medium/high (~0.54) ─────────────────────────────────────
    {
        "_name": "Borderline medium/high (~0.54)",
        "_expected_zone": "RESALE",
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

    # ── 7 Borderline low/medium (~0.35) ──────────────────────────────────────
    {
        "_name": "Borderline low/medium (~0.35)",
        "_expected_zone": "REDEPLOY",
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

    # ── 8 Old but well-maintained ─────────────────────────────────────────────
    {
        "_name": "Old but well-maintained",
        "_expected_zone": "REDEPLOY",
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

    # ── 9 Partial telemetry (data_completeness=0.45 → policy-only path) ──────
    {
        "_name": "Partial telemetry (completeness=0.45)",
        "_expected_zone": "REDEPLOY",
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
        "data_completeness": 0.45,   # ← triggers policy-only path (ML skipped)
    },

    # ── 10 High incidents, young device ──────────────────────────────────────
    {
        "_name": "High incidents, young device",
        "_expected_zone": "RESALE",
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


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------

# ANSI colour codes
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_CYAN   = "\033[96m"
_GREY   = "\033[90m"

_ACTION_COLOUR = {
    "RECYCLE":   _RED,
    "REPAIR":    _YELLOW,
    "REFURBISH": _YELLOW,
    "RESALE":    _GREEN,
    "REDEPLOY":  _GREEN,
}

_ACTION_ICON = {
    "RECYCLE":   "🔴",
    "REPAIR":    "🟠",
    "REFURBISH": "🟡",
    "RESALE":    "🟢",
    "REDEPLOY":  "🔵",
}


def _colour_action(action: str) -> str:
    col  = _ACTION_COLOUR.get(action, "")
    icon = _ACTION_ICON.get(action, "")
    return f"{col}{_BOLD}{icon} {action}{_RESET}"


def _print_separator(char: str = "─", width: int = 80) -> None:
    print(char * width)


def _print_result(idx: int, scenario: dict, result: dict) -> None:
    """Print one scenario result in a human-readable multi-section layout."""
    name          = scenario["_name"]
    expected_zone = scenario["_expected_zone"]
    expected_score = scenario["_expected_risk_score"]

    ml     = result.get("ml_result", {})
    policy = result.get("policy_result", {})
    llm    = result.get("llm_result", {})
    action = result.get("final_action", "?")

    _print_separator("═")
    print(f"{_BOLD}Scenario {idx:02d}/{len(SCENARIOS)}  —  {name}{_RESET}")
    _print_separator()

    # ── Expected vs actual ─────────────────────────────────────────────────
    match = action == expected_zone
    status_icon = f"{_GREEN}✅ MATCH{_RESET}" if match else f"{_YELLOW}⚠  MISMATCH{_RESET}"
    print(f"  Expected action  : {_colour_action(expected_zone)}  (notebook score ≈ {expected_score:.3f})")
    print(f"  Final action     : {_colour_action(action)}   {status_icon}")
    print(f"  Confidence score : {result.get('confidence_score', '?'):.4f}")

    # ── ML result ─────────────────────────────────────────────────────────
    print(f"\n  {_BOLD}[ML Model]{_RESET}")
    if ml.get("ml_available"):
        print(f"    Risk label   : {_BOLD}{ml['risk_label'].upper()}{_RESET}")
        print(f"    Risk score   : {ml['risk_score']:.4f}")
        print(f"    Confidence   : {ml['confidence_band']}")
        print(f"    P(high)={ml['p_high']:.4f}   P(medium)={ml['p_medium']:.4f}   P(low)={ml['p_low']:.4f}")
    else:
        print(f"    {_GREY}ML skipped — data_completeness below threshold (policy-only path){_RESET}")
        print(f"    Risk score (formula) : {ml.get('risk_score', '?'):.4f}")

    # ── Policy result ──────────────────────────────────────────────────────
    print(f"\n  {_BOLD}[Policy Engine]{_RESET}")
    print(f"    Classification  : {policy.get('classification', '?')}")
    rules = policy.get("triggered_rules", [])
    print(f"    Triggered rules : {', '.join(rules) if rules else 'none'}")
    for sig in policy.get("supporting_signals", []):
        print(f"      • {sig}")

    # ── LLM result ────────────────────────────────────────────────────────
    print(f"\n  {_BOLD}[LLM Engine]{_RESET}")
    llm_tag = f"{_GREEN}live{_RESET}" if llm.get("llm_available") else f"{_YELLOW}fallback template{_RESET}"
    print(f"    Source : {llm_tag}")
    explanation = llm.get("explanation", "")
    wrapped = textwrap.fill(explanation, width=72, initial_indent="    ", subsequent_indent="    ")
    print(f"\n  Explanation:\n{wrapped}")

    task = llm.get("itsm_task", {})
    if task:
        print(f"\n  ITSM Task:")
        print(f"    Title    : {task.get('title', '?')}")
        print(f"    Priority : {task.get('priority', '?')}")
        print(f"    Team     : {task.get('assigned_team', '?')}")
        checklist = task.get("checklist", [])
        if checklist:
            print(f"    Checklist ({len(checklist)} steps):")
            for step in checklist:
                print(f"      ☐ {step}")

    print()


def _print_summary(results: list[dict]) -> None:
    """Print a final pass/fail summary table."""
    _print_separator("═")
    print(f"{_BOLD}SUMMARY — {len(results)} scenarios{_RESET}")
    _print_separator()
    passes = 0
    for r in results:
        idx      = r["idx"]
        name     = r["name"]
        expected = r["expected"]
        actual   = r["actual"]
        ok       = expected == actual
        if ok:
            passes += 1
        icon = f"{_GREEN}✅{_RESET}" if ok else f"{_YELLOW}⚠ {_RESET}"
        print(f"  {icon} S{idx:02d}  {name:<38}  expected={expected:<10}  got={actual}")
    _print_separator()
    colour = _GREEN if passes == len(results) else _YELLOW
    print(f"  {colour}{_BOLD}{passes}/{len(results)} scenarios matched expected lifecycle zone{_RESET}")
    _print_separator("═")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def _strip_private(d: dict) -> dict:
    """Remove _name / _expected_* keys before sending to the API."""
    return {k: v for k, v in d.items() if not k.startswith("_")}


def run_tests(base_url: str, stop_on_error: bool = False) -> None:
    endpoint = f"{base_url.rstrip('/')}/analyse_device"
    print(f"\n{_BOLD}E-Waste Asset Lifecycle Optimizer — API Scenario Tests{_RESET}")
    print(f"Endpoint : {endpoint}")
    print(f"Scenarios: {len(SCENARIOS)}")
    _print_separator("═")

    summary_rows: list[dict] = []

    for idx, scenario in enumerate(SCENARIOS, start=1):
        payload = _strip_private(scenario)

        print(f"\n{_GREY}→ Sending scenario {idx:02d}: {scenario['_name']}{_RESET}")

        try:
            response = requests.post(endpoint, json=payload, timeout=30)
        except requests.ConnectionError:
            print(f"  {_RED}✗ Connection refused — is the server running at {base_url}?{_RESET}")
            if stop_on_error:
                sys.exit(1)
            continue
        except requests.Timeout:
            print(f"  {_RED}✗ Request timed out after 30 s{_RESET}")
            if stop_on_error:
                sys.exit(1)
            continue

        if response.status_code != 200:
            print(f"  {_RED}✗ HTTP {response.status_code}: {response.text[:300]}{_RESET}")
            if stop_on_error:
                sys.exit(1)
            continue

        result = response.json()
        _print_result(idx, scenario, result)

        summary_rows.append({
            "idx":      idx,
            "name":     scenario["_name"],
            "expected": scenario["_expected_zone"],
            "actual":   result.get("final_action", "ERROR"),
        })

    if summary_rows:
        _print_summary(summary_rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the 10 hand-crafted scenarios against the FastAPI /analyse_device endpoint"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the running API server (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately on the first HTTP error response",
    )
    args = parser.parse_args()
    run_tests(base_url=args.url, stop_on_error=args.stop_on_error)
