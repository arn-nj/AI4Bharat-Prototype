"""Assets router — CRUD for device inventory."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db.database import AssetRow, RiskAssessmentRow, get_db
from ..orm_models.asset import AssetCreate, AssetOut

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _age_from_purchase(purchase_date: str) -> int:
    try:
        pd_dt = datetime.fromisoformat(purchase_date.replace("Z", "+00:00"))
        now   = datetime.now(timezone.utc)
        return max(0, int((now - pd_dt).days / 30))
    except Exception:
        return 0


def _data_completeness(payload: AssetCreate) -> float:
    telemetry_fields = [payload.battery_cycles, payload.smart_sectors_reallocated, payload.thermal_events_count,
                        payload.battery_health_pct, payload.performance_rating]
    ticket_fields    = [payload.total_incidents, payload.critical_incidents, payload.avg_resolution_time_hours]
    filled = sum(1 for f in telemetry_fields + ticket_fields if f is not None)
    return round(filled / 8, 2)


@router.post("", response_model=AssetOut, status_code=201)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).isoformat()
    current_year = datetime.now(timezone.utc).year
    age = payload.model_year and (current_year - payload.model_year) * 12 or (
        _age_from_purchase(payload.purchase_date) if payload.purchase_date else 0
    )
    completeness = _data_completeness(payload)

    asset = AssetRow(
        device_type=payload.device_type,
        brand=payload.brand,
        serial_number=payload.serial_number,
        model_name=payload.model_name,
        model_year=payload.model_year,
        os=payload.os,
        purchase_date=payload.purchase_date or now,
        department=payload.department,
        region=payload.region,
        age_months=age,
        data_completeness=completeness,
        usage_type=payload.usage_type,
        daily_usage_hours=payload.daily_usage_hours,
        performance_rating=payload.performance_rating,
        battery_health_pct=payload.battery_health_pct,
        overheating_issues=str(payload.overheating_issues) if payload.overheating_issues is not None else None,
        battery_cycles=payload.battery_cycles,
        smart_sectors_reallocated=payload.smart_sectors_reallocated,
        thermal_events_count=payload.thermal_events_count,
        total_incidents=payload.total_incidents,
        critical_incidents=payload.critical_incidents,
        high_incidents=payload.high_incidents,
        medium_incidents=payload.medium_incidents,
        low_incidents=payload.low_incidents,
        avg_resolution_time_hours=payload.avg_resolution_time_hours,
        current_state="active",
        created_at=now,
        updated_at=now,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return AssetOut(**asset.__dict__)


@router.get("", response_model=List[AssetOut])
def list_assets(
    department: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(AssetRow)
    if department:
        q = q.filter_by(department=department)
    if region:
        q = q.filter_by(region=region)
    if state:
        q = q.filter_by(current_state=state)
    rows = q.order_by(AssetRow.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    # Resolve last_assessed_at from risk_assessments (source of truth, not updated_at)
    asset_ids = [r.asset_id for r in rows]
    risk_rows = db.query(RiskAssessmentRow.asset_id, RiskAssessmentRow.assessed_at)\
        .filter(RiskAssessmentRow.asset_id.in_(asset_ids)).all()
    risk_map: dict[str, str] = {}
    for ar_id, ar_at in risk_rows:
        if ar_id not in risk_map or (ar_at or '') > risk_map[ar_id]:
            risk_map[ar_id] = ar_at or ''
    return [AssetOut(**r.__dict__, last_assessed_at=risk_map.get(r.asset_id)) for r in rows]


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: str, db: Session = Depends(get_db)):
    row = db.query(AssetRow).filter_by(asset_id=asset_id).first()
    if not row:
        raise HTTPException(404, f"Asset {asset_id} not found")
    risk_row = db.query(RiskAssessmentRow).filter_by(asset_id=asset_id)\
        .order_by(RiskAssessmentRow.assessed_at.desc()).first()
    return AssetOut(**row.__dict__, last_assessed_at=risk_row.assessed_at if risk_row else None)


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: str, db: Session = Depends(get_db)):
    row = db.query(AssetRow).filter_by(asset_id=asset_id).first()
    if not row:
        raise HTTPException(404, f"Asset {asset_id} not found")
    db.delete(row)
    db.commit()
