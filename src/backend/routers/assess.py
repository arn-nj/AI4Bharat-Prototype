"""Assessment router — run risk assessment + generate recommendation."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from ..db.database import AssetRow, get_db
from ..orm_models.recommendation import AssessmentResultOut, LLMPrediction
from ..services import risk_engine, recommendation as rec_svc
from ..services import llm as llm_svc

router = APIRouter(prefix="/api/assess", tags=["assess"])


@router.post("/{asset_id}", response_model=AssessmentResultOut)
def assess_asset(asset_id: str, db: Session = Depends(get_db)):
    """Run full assessment pipeline: risk → recommendation → ITSM scaffold + LLM prediction."""
    asset = db.query(AssetRow).filter_by(asset_id=asset_id).first()
    if not asset:
        raise HTTPException(404, f"Asset {asset_id} not found")

    risk_result = risk_engine.assess_asset(asset, db)
    rec_result  = rec_svc.generate_recommendation(asset, risk_result, db)

    # Stamp last-assessed time so inventory can sort by it
    asset.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()

    # LLM independent prediction (parallel second opinion)
    llm_pred_raw = llm_svc.llm_predict(asset)
    llm_prediction = None
    if llm_pred_raw and isinstance(llm_pred_raw, dict):
        llm_prediction = LLMPrediction(
            risk_level=llm_pred_raw.get("risk_level", "unknown"),
            action=llm_pred_raw.get("action", "unknown"),
            reasoning=llm_pred_raw.get("reasoning", ""),
            agrees_with_ml=(
                llm_pred_raw.get("risk_level", "").lower() == risk_result.risk_level.value.lower()
            ),
        )

    return AssessmentResultOut(
        asset_id=asset_id,
        risk=risk_result,
        recommendation=rec_result,
        llm_prediction=llm_prediction,
    )
