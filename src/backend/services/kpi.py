"""
KPI Calculation Service — fleet metrics with environmental impact.

Environmental impact estimates (industry averages):
  - Each recycled laptop: ~25 kg CO₂ saved vs. landfill + manufacturing new
  - Each repaired device: ~10 kg CO₂ saved (vs. new)
  - Each refurbished device: ~5 kg CO₂ saved
  - Average laptop weight: 2.1 kg
  - 1 tree absorbs ~21 kg CO₂ per year
  - Rare earth metal recovery from e-waste recycling: ~75% recovery rate
"""

from __future__ import annotations

from collections import Counter
from typing import Dict

from sqlalchemy.orm import Session

from ..db.database import AssetRow, RiskAssessmentRow, RecommendationRow, AuditRow
from ..orm_models.audit import KPIOut

AVG_REPLACEMENT_COST = 85000.0  # INR — mid-range laptop replacement cost in India
AVG_DEVICE_WEIGHT_KG = 2.1

# CO₂ savings per action (kg)
CO2_PER_ACTION = {
    "recycle":   25.0,
    "repair":    10.0,
    "refurbish":  5.0,
    "redeploy":   3.0,
    "resale":     2.0,
}


def calculate_kpis(db: Session) -> KPIOut:
    assets = db.query(AssetRow).all()
    risks  = db.query(RiskAssessmentRow).all()
    recs   = db.query(RecommendationRow).all()
    audits = db.query(AuditRow).all()

    total = len(assets)
    if total == 0:
        return _empty_kpis()

    risk_map: Dict[str, str] = {r.asset_id: r.risk_level for r in risks}
    high   = sum(1 for v in risk_map.values() if v == "high")
    medium = sum(1 for v in risk_map.values() if v == "medium")
    low    = sum(1 for v in risk_map.values() if v == "low")

    avg_age  = sum(a.age_months for a in assets) / total
    approved = sum(1 for a in audits if a.decision == "approved")
    rejected = sum(1 for a in audits if a.decision == "rejected")
    pending  = sum(1 for a in assets if a.current_state == "review_pending")

    non_recycle = sum(1 for r in recs if r.action != "recycle")
    deferred_spend = non_recycle * AVG_REPLACEMENT_COST

    action_counts = Counter(r.action for r in recs)
    action_pct: Dict[str, float] = {}
    rec_total = len(recs)
    if rec_total > 0:
        action_pct = {k: round(v / rec_total * 100, 1) for k, v in action_counts.items()}

    dept_counts = Counter(a.department for a in assets)

    risk_by_dept: Dict[str, Dict[str, int]] = {}
    for a in assets:
        dept = a.department
        if dept not in risk_by_dept:
            risk_by_dept[dept] = {"high": 0, "medium": 0, "low": 0}
        level = risk_map.get(a.asset_id, "low")
        risk_by_dept[dept][level] = risk_by_dept[dept].get(level, 0) + 1

    # Environmental impact
    co2_saved = sum(
        CO2_PER_ACTION.get(r.action, 0) for r in recs
    )
    landfill_kg = action_counts.get("recycle", 0) * AVG_DEVICE_WEIGHT_KG
    + action_counts.get("repair", 0) * AVG_DEVICE_WEIGHT_KG * 0.5
    carbon_trees = int(co2_saved / 21)
    recycle_count = action_counts.get("recycle", 0)
    material_pct = 75.0 if recycle_count > 0 else 0.0

    return KPIOut(
        total_assets=total,
        high_risk=high,
        medium_risk=medium,
        low_risk=low,
        avg_age_months=round(avg_age, 1),
        assessed_count=len(risks),
        pending_approval=pending,
        approved_count=approved,
        rejected_count=rejected,
        deferred_spend_inr=deferred_spend,
        lifecycle_actions=dict(action_counts),
        action_percentages=action_pct,
        departments=dict(dept_counts),
        risk_by_department=risk_by_dept,
        co2_saved_kg=round(co2_saved, 1),
        landfill_reduction_kg=round(landfill_kg, 1),
        carbon_offset_trees=carbon_trees,
        material_recovery_pct=material_pct,
    )


def _empty_kpis() -> KPIOut:
    return KPIOut(
        total_assets=0, high_risk=0, medium_risk=0, low_risk=0,
        avg_age_months=0.0, assessed_count=0, pending_approval=0,
        approved_count=0, rejected_count=0, deferred_spend_inr=0.0,
        lifecycle_actions={}, action_percentages={},
        departments={}, risk_by_department={},
        co2_saved_kg=0.0, landfill_reduction_kg=0.0,
        carbon_offset_trees=0, material_recovery_pct=0.0,
    )
