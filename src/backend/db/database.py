"""
SQLAlchemy ORM for the E-Waste Asset Lifecycle Optimizer.

Production: Amazon RDS (PostgreSQL) — set DATABASE_URL env var.
Local dev:  SQLite fallback when DATABASE_URL is not set.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, Float, Text, create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


# ── ORM Tables ────────────────────────────────────────────────

class AssetRow(Base):
    __tablename__ = "assets"
    asset_id = Column(String, primary_key=True, default=lambda: f"ASSET-{uuid.uuid4().hex[:8]}")
    device_type = Column(String, nullable=False)
    brand = Column(String, nullable=True)
    model_name = Column(String, nullable=True)
    model_year = Column(Integer, nullable=True)
    os = Column(String, nullable=True)
    purchase_date = Column(String, nullable=True)
    department = Column(String, nullable=False)
    region = Column(String, nullable=False)
    current_state = Column(String, nullable=False, default="active")
    age_months = Column(Integer, nullable=False)
    data_completeness = Column(Float, nullable=False, default=0.0)
    updated_at = Column(String, nullable=True)
    # telemetry (nullable = graceful degradation)
    battery_cycles = Column(Integer, nullable=True)
    smart_sectors_reallocated = Column(Integer, nullable=True)
    thermal_events_count = Column(Integer, nullable=True)
    # ticket aggregate
    total_incidents = Column(Integer, nullable=True)
    critical_incidents = Column(Integer, nullable=True)
    high_incidents = Column(Integer, nullable=True)
    medium_incidents = Column(Integer, nullable=True)
    low_incidents = Column(Integer, nullable=True)
    avg_resolution_time_hours = Column(Float, nullable=True)
    created_at = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())


class RiskAssessmentRow(Base):
    __tablename__ = "risk_assessments"
    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:12])
    asset_id = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False)
    confidence_band = Column(String, nullable=False)
    eval_mode = Column(String, nullable=False)
    triggered_rules_json = Column(Text, nullable=False, default="[]")
    # ML model fields (nullable — policy-only path doesn't fill these)
    ml_risk_label = Column(String, nullable=True)
    ml_p_high = Column(Float, nullable=True)
    ml_p_medium = Column(Float, nullable=True)
    ml_p_low = Column(Float, nullable=True)
    policy_version = Column(String, nullable=False, default="v1.0")
    assessed_at = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())


class RecommendationRow(Base):
    __tablename__ = "recommendations"
    recommendation_id = Column(String, primary_key=True, default=lambda: f"REC-{uuid.uuid4().hex[:8]}")
    asset_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    rationale = Column(Text, nullable=False)
    supporting_signals_json = Column(Text, nullable=False, default="[]")
    itsm_task_json = Column(Text, nullable=True)   # LLM-generated ITSM task (JSON)
    policy_version = Column(String, nullable=False, default="v1.0")
    model_version = Column(String, nullable=False, default="policy-only")
    created_at = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())


class AuditRow(Base):
    __tablename__ = "audit_trail"
    audit_id = Column(String, primary_key=True, default=lambda: f"AUD-{uuid.uuid4().hex[:8]}")
    recommendation_id = Column(String, nullable=False)
    asset_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    decision = Column(String, nullable=False)
    rationale = Column(Text, nullable=False)
    actor = Column(String, nullable=False)
    previous_state = Column(String, nullable=False)
    new_state = Column(String, nullable=False)
    asset_snapshot_json = Column(Text, nullable=False)
    recommendation_snapshot_json = Column(Text, nullable=False)
    llm_impact = Column(Text, nullable=True)
    timestamp = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())


class PolicyConfigRow(Base):
    __tablename__ = "policy_config"
    id = Column(String, primary_key=True, default="default")
    age_threshold_months = Column(Integer, default=42)
    ticket_threshold = Column(Integer, default=5)
    thermal_threshold = Column(Integer, default=10)
    smart_sector_threshold = Column(Integer, default=50)
    policy_version = Column(String, default="v1.0")
    updated_at = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())


# ── Engine + Session ──────────────────────────────────────────

import os

# Production: postgresql+psycopg2://user:pass@rds-host:5432/ewaste
# Local dev:  sqlite:///./ewaste.db  (fallback when env var is absent)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./ewaste.db")

_IS_SQLITE = DATABASE_URL.startswith("sqlite")

if _IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
else:
    # RDS PostgreSQL — pool_pre_ping keeps connections alive across Lambda invocations
    # connect_timeout=10 ensures fast failure instead of hanging on cold start
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=2,        # Lambda concurrency: keep pool small
        max_overflow=5,
        pool_recycle=300,   # recycle connections every 5 min (RDS idle timeout)
        pool_timeout=15,    # give up waiting for a pool slot after 15s
        connect_args={"connect_timeout": 10},  # TCP connect timeout in seconds
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create tables and seed default policy config."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if not db.query(PolicyConfigRow).first():
            db.add(PolicyConfigRow())
            db.commit()


def get_db():
    """FastAPI dependency — yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
