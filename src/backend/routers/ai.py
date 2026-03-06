"""AI Assistant router — conversational queries + policy suggestions."""

from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from ..db.database import AssetRow, RecommendationRow, get_db
from ..orm_models.audit import KPIOut
from ..orm_models.recommendation import LLMPrediction
from ..services import kpi as kpi_svc
from ..services import llm as llm_svc

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    response: str


class PolicySuggestRequest(BaseModel):
    age_threshold_months: int = 42
    ticket_threshold: int = 5
    thermal_threshold: int = 10
    smart_sector_threshold: int = 50


class AnalyzeDocRequest(BaseModel):
    document_type: str = "certificate"   # certificate | invoice | chain_of_custody
    region: str = "India"
    asset_id: str = ""
    file_content: str


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """Chat with the AI Assistant about your fleet."""
    kpis = kpi_svc.calculate_kpis(db)
    context = (
        f"Fleet summary: {kpis.total_assets} total assets. "
        f"Risk: {kpis.high_risk} high, {kpis.medium_risk} medium, {kpis.low_risk} low. "
        f"CO2 saved: {kpis.co2_saved_kg} kg. "
        f"Pending approvals: {kpis.pending_approval}. "
        f"Actions: {kpis.lifecycle_actions}."
    )
    response = llm_svc.chat(query=payload.query, context=context)
    return ChatResponse(response=response)


@router.post("/suggest-policy")
def suggest_policy(payload: PolicySuggestRequest):
    """Get LLM-powered recommendations on policy threshold tuning."""
    suggestion = llm_svc.suggest_policy(payload.model_dump())
    return {"suggestion": suggestion}


@router.get("/fleet-narrative")
def fleet_narrative(db: Session = Depends(get_db)):
    """Return an AI-generated executive summary of current fleet health."""
    kpis = kpi_svc.calculate_kpis(db)
    narrative = llm_svc.fleet_narrative(kpis)
    return {"narrative": narrative}


@router.post("/analyze-doc")
def analyze_doc(payload: AnalyzeDocRequest):
    """Analyse a compliance document and return structured extraction results."""
    result = llm_svc.analyze_compliance_doc(
        document_type=payload.document_type,
        region=payload.region,
        asset_id=payload.asset_id,
        file_content=payload.file_content,
    )
    return result


@router.get("/predict/{asset_id}", response_model=LLMPrediction)
def predict_asset(asset_id: str, db: Session = Depends(get_db)):
    """Return (and persist) an independent LLM risk + action opinion for an asset."""
    import json
    asset = db.query(AssetRow).filter_by(asset_id=asset_id).first()
    if not asset:
        raise HTTPException(404, f"Asset {asset_id} not found")

    raw = llm_svc.llm_predict(asset)
    if not raw:
        raise HTTPException(503, "LLM prediction unavailable")

    prediction = LLMPrediction(**raw)

    # Persist on the most recent recommendation so approval service can reference it
    rec = (
        db.query(RecommendationRow)
        .filter_by(asset_id=asset_id)
        .order_by(RecommendationRow.created_at.desc())
        .first()
    )
    if rec:
        rec.llm_prediction_json = json.dumps(prediction.model_dump())
        db.commit()

    return prediction


@router.get("/predict/{asset_id}", response_model=LLMPrediction)
def predict_asset(asset_id: str, db: Session = Depends(get_db)):
    """LLM independent risk prediction for an existing asset (second opinion)."""
    asset = db.query(AssetRow).filter_by(asset_id=asset_id).first()
    if not asset:
        raise HTTPException(404, f"Asset {asset_id} not found")
    result = llm_svc.llm_predict(asset)
    if not result or not isinstance(result, dict):
        return LLMPrediction(
            risk_level="unknown", action="unknown",
            reasoning="LLM service unavailable — try again shortly.",
        )
    return LLMPrediction(
        risk_level=result.get("risk_level", "unknown"),
        action=result.get("action", "unknown"),
        reasoning=result.get("reasoning", ""),
    )
