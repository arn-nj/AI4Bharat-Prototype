"""KPIs router — fleet performance metrics + environmental impact."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from ..db.database import get_db
from ..orm_models.audit import KPIOut
from ..services import kpi as kpi_svc

router = APIRouter(prefix="/api/kpis", tags=["kpis"])


@router.get("", response_model=KPIOut)
def get_kpis(db: Session = Depends(get_db)):
    return kpi_svc.calculate_kpis(db)
