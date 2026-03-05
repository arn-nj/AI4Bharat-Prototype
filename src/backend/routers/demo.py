"""Demo router — generate synthetic device fleets for testing."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional

from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from ..db.database import get_db
from ..services import data_generator as gen_svc
from ..services import risk_engine, recommendation as rec_svc
from ..db.database import AssetRow

router = APIRouter(prefix="/api/demo", tags=["demo"])


class GenerateRequest(BaseModel):
    count: int = Field(default=10, ge=1, le=50)
    department: Optional[str] = None
    region: Optional[str] = None
    auto_assess: bool = Field(default=True, description="Run assessment on generated assets")


@router.post("/generate")
def generate(payload: GenerateRequest, db: Session = Depends(get_db)):
    """Generate a synthetic fleet and optionally run assessments."""
    assets = gen_svc.generate_fleet(
        count=payload.count,
        department=payload.department,
        region=payload.region,
        db=db,
    )

    assessed = 0
    if payload.auto_assess:
        for asset in assets:
            try:
                risk = risk_engine.assess_asset(asset, db)
                rec_svc.generate_recommendation(asset, risk, db)
                assessed += 1
            except Exception:
                pass  # continue with others even if one fails

    return {
        "generated": len(assets),
        "assessed": assessed,
        "asset_ids": [a.asset_id for a in assets],
        "message": (
            f"Generated {len(assets)} synthetic assets"
            + (f", assessed {assessed}" if payload.auto_assess else "")
            + "."
        ),
    }


@router.delete("/reset")
def reset_demo(db: Session = Depends(get_db)):
    """Wipe all data from the database (demo use only!)."""
    from ..db.database import AssetRow, RiskAssessmentRow, RecommendationRow, AuditRow
    db.query(AuditRow).delete()
    db.query(RecommendationRow).delete()
    db.query(RiskAssessmentRow).delete()
    db.query(AssetRow).delete()
    db.commit()
    return {"message": "All data cleared."}
