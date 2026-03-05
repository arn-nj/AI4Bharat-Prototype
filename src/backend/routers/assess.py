"""Assessment router — run risk assessment + generate recommendation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from ..db.database import AssetRow, get_db
from ..orm_models.recommendation import AssessmentResultOut
from ..services import risk_engine, recommendation as rec_svc

router = APIRouter(prefix="/api/assess", tags=["assess"])


@router.post("/{asset_id}", response_model=AssessmentResultOut)
def assess_asset(asset_id: str, db: Session = Depends(get_db)):
    """Run full assessment pipeline: risk → recommendation → ITSM scaffold."""
    asset = db.query(AssetRow).filter_by(asset_id=asset_id).first()
    if not asset:
        raise HTTPException(404, f"Asset {asset_id} not found")

    risk_result  = risk_engine.assess_asset(asset, db)
    rec_result   = rec_svc.generate_recommendation(asset, risk_result, db)

    return AssessmentResultOut(
        asset_id=asset_id,
        risk=risk_result,
        recommendation=rec_result,
    )
