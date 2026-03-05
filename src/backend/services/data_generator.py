"""
Demo Data Generator — creates synthetic device fleets for testing.

Generates realistic asset profiles covering the same device categories
and feature distributions present in the training CSV
(training_data_phase5_1235records_fixed.csv).
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from ..db.database import AssetRow, init_db

# ── Vocabulary ────────────────────────────────────────────────
DEVICE_TYPES  = ["Laptop", "Desktop", "Server", "Tablet", "Workstation"]
BRANDS        = ["HP", "Dell", "Apple", "Lenovo", "Asus", "Acer", "Microsoft", "Toshiba"]
DEPARTMENTS   = ["Engineering", "HR", "Finance", "Operations", "IT", "Sales", "Marketing", "Legal"]
REGIONS       = ["North", "South", "East", "West", "Central"]
OS_LIST       = ["Windows 11", "Windows 10", "macOS 14", "Ubuntu 22.04", "ChromeOS"]

# ── Profile distributions ─────────────────────────────────────

def _random_profile(device_type: str) -> dict:
    """Generate a realistic device profile with weighted risk distribution."""
    rng = random.random()

    if rng < 0.30:  # High-risk profile
        age          = random.randint(48, 84)
        incidents    = random.randint(8, 20)
        critical_inc = random.randint(2, incidents)
        high_inc     = random.randint(1, max(1, incidents - critical_inc))
        batt_cycles  = random.randint(700, 1500) if device_type in ("Laptop", "Tablet") else None
        thermal      = random.randint(8, 25)
        smart        = random.randint(40, 120)
        data_comp    = round(random.uniform(0.70, 1.0), 2)
    elif rng < 0.60:  # Medium-risk profile
        age          = random.randint(24, 48)
        incidents    = random.randint(3, 8)
        critical_inc = random.randint(0, 2)
        high_inc     = random.randint(1, 3)
        batt_cycles  = random.randint(200, 700) if device_type in ("Laptop", "Tablet") else None
        thermal      = random.randint(2, 8)
        smart        = random.randint(5, 40)
        data_comp    = round(random.uniform(0.60, 0.85), 2)
    else:  # Low-risk profile
        age          = random.randint(1, 24)
        incidents    = random.randint(0, 3)
        critical_inc = 0
        high_inc     = random.randint(0, 1)
        batt_cycles  = random.randint(0, 200) if device_type in ("Laptop", "Tablet") else None
        thermal      = random.randint(0, 2)
        smart        = random.randint(0, 5)
        data_comp    = round(random.uniform(0.40, 0.70), 2)

    low_inc = max(0, incidents - critical_inc - high_inc)
    medium_inc = max(0, incidents - critical_inc - high_inc - low_inc)

    return dict(
        age_months=age,
        total_incidents=incidents,
        critical_incidents=critical_inc,
        high_incidents=high_inc,
        medium_incidents=medium_inc,
        low_incidents=low_inc,
        avg_resolution_time_hours=round(random.uniform(2.0, 72.0), 1),
        battery_cycles=batt_cycles,
        thermal_events_count=thermal,
        smart_sectors_reallocated=smart,
        data_completeness=data_comp,
    )


def generate_fleet(
    count: int,
    department: str | None,
    region: str | None,
    db: Session,
) -> List[AssetRow]:
    """Generate `count` randomised assets and persist them to the DB."""
    created: List[AssetRow] = []
    now = datetime.now(timezone.utc).isoformat()

    for _ in range(count):
        dtype = random.choice(DEVICE_TYPES)
        profile = _random_profile(dtype)
        dept   = department or random.choice(DEPARTMENTS)
        reg    = region    or random.choice(REGIONS)

        brand = random.choice(BRANDS)
        os    = random.choice(OS_LIST)
        year  = 2024 - (profile["age_months"] // 12)

        asset = AssetRow(
            asset_id=str(uuid.uuid4()),
            device_type=dtype,
            brand=brand,
            model_name=f"{brand} {dtype} {year}",
            model_year=year,
            department=dept,
            region=reg,
            os=os,
            age_months=profile["age_months"],
            total_incidents=profile["total_incidents"],
            critical_incidents=profile["critical_incidents"],
            high_incidents=profile["high_incidents"],
            medium_incidents=profile["medium_incidents"],
            low_incidents=profile["low_incidents"],
            avg_resolution_time_hours=profile["avg_resolution_time_hours"],
            battery_cycles=profile["battery_cycles"],
            thermal_events_count=profile["thermal_events_count"],
            smart_sectors_reallocated=profile["smart_sectors_reallocated"],
            data_completeness=profile["data_completeness"],
            current_state="active",
            created_at=now,
            updated_at=now,
        )
        db.add(asset)
        created.append(asset)

    db.commit()
    return created
