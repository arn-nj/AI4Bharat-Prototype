"""Asset Pydantic schemas — request/response models."""

from __future__ import annotations

import enum
from typing import Optional
from pydantic import BaseModel, Field


class AssetState(str, enum.Enum):
    ACTIVE = "active"
    REVIEW_PENDING = "review_pending"
    APPROVED_FOR_REDEPLOY = "approved_for_redeploy"
    APPROVED_FOR_REPAIR = "approved_for_repair"
    APPROVED_FOR_REFURBISH = "approved_for_refurbish"
    APPROVED_FOR_RESALE = "approved_for_resale"
    APPROVED_FOR_RECYCLE = "approved_for_recycle"
    WORKFLOW_IN_PROGRESS = "workflow_in_progress"
    CLOSED = "closed"
    EXCEPTION = "exception"


class DeviceType(str, enum.Enum):
    LAPTOP = "laptop"
    SERVER = "server"


class Region(str, enum.Enum):
    INDIA = "India"
    US = "US"
    EU = "EU"


class AssetCreate(BaseModel):
    """Form payload for manual device entry."""
    device_type: str
    brand: Optional[str] = None
    model_name: Optional[str] = None
    model_year: Optional[int] = None
    os: Optional[str] = None
    purchase_date: Optional[str] = Field(None, description="ISO date string, e.g. 2022-03-15")
    department: str
    region: str
    battery_cycles: Optional[int] = None
    smart_sectors_reallocated: Optional[int] = None
    thermal_events_count: Optional[int] = None
    total_incidents: Optional[int] = None
    critical_incidents: Optional[int] = None
    high_incidents: Optional[int] = None
    medium_incidents: Optional[int] = None
    low_incidents: Optional[int] = None
    avg_resolution_time_hours: Optional[float] = None


class AssetOut(BaseModel):
    asset_id: str
    device_type: str
    brand: Optional[str] = None
    model_name: Optional[str] = None
    model_year: Optional[int] = None
    os: Optional[str] = None
    purchase_date: Optional[str] = None
    department: str
    region: str
    current_state: str
    age_months: int
    data_completeness: float
    battery_cycles: Optional[int] = None
    smart_sectors_reallocated: Optional[int] = None
    thermal_events_count: Optional[int] = None
    total_incidents: Optional[int] = None
    critical_incidents: Optional[int] = None
    high_incidents: Optional[int] = None
    medium_incidents: Optional[int] = None
    low_incidents: Optional[int] = None
    avg_resolution_time_hours: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
