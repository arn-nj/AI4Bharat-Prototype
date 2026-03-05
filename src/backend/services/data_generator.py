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
DEVICE_TYPES  = [
    "Laptop", "Desktop", "Server", "Tablet", "Workstation",
    "Printer", "Network Device", "Mobile Phone", "Monitor", "Projector",
]
BRANDS        = ["HP", "Dell", "Apple", "Lenovo", "Asus", "Acer", "Microsoft", "Toshiba", "Samsung", "Canon"]
DEPARTMENTS   = ["Engineering", "HR", "Finance", "Operations", "IT", "Sales", "Marketing", "Legal"]
# Indian office locations (major IT hub cities / states)
REGIONS       = [
    "Mumbai", "Bengaluru", "Chennai", "Hyderabad", "Delhi NCR",
    "Pune", "Kolkata", "Ahmedabad", "Kochi", "Noida",
]
OS_LIST       = ["Windows 11", "Windows 10", "macOS 14", "Ubuntu 22.04", "ChromeOS", "Android 14", "iOS 17"]
USAGE_TYPES   = ["Standard", "Development", "Creative", "Intensive", "Light"]

# ── Profile distributions ─────────────────────────────────────

def _random_profile(device_type: str) -> dict:
    """Generate a realistic device profile with weighted risk distribution.

    Risk buckets (approximate):
      30% High   — old + heavy incidents       → RECYCLE
      15% High   — young + hardware failure    → REPAIR  (thermal/SMART issues without age trigger)
      25% Medium — moderate wear               → REFURBISH
      20% Low    — young + new                 → REDEPLOY
      10% Low    — aging but low incidents     → RESALE
    """
    rng = random.random()

    if rng < 0.30:  # High-risk: old + heavy incidents → RECYCLE
        age          = random.randint(48, 84)
        incidents    = random.randint(8, 20)
        critical_inc = random.randint(2, incidents)
        high_inc     = random.randint(1, max(1, incidents - critical_inc))
        batt_cycles  = random.randint(700, 1500) if device_type in ("Laptop", "Tablet", "Mobile Phone") else None
        batt_health  = round(random.uniform(30, 60), 1) if batt_cycles else None
        thermal      = random.randint(8, 25)
        smart        = random.randint(40, 120)
        perf_rating  = random.randint(1, 2)
        daily_hours  = round(random.uniform(6, 14), 1)
        usage_type   = random.choice(["Intensive", "Development"])
        overheating  = thermal > 10
        data_comp    = round(random.uniform(0.70, 1.0), 2)

    elif rng < 0.45:  # High-risk: young + hardware failure → REPAIR
        # age < 42 so age_and_tickets won't fire; thermal/smart ARE above threshold
        age          = random.randint(12, 36)
        incidents    = random.randint(0, 4)          # below ticket threshold (5)
        critical_inc = random.randint(0, min(2, incidents))
        high_inc     = random.randint(0, max(0, incidents - critical_inc))
        batt_cycles  = random.randint(400, 800) if device_type in ("Laptop", "Tablet", "Mobile Phone") else None
        batt_health  = round(random.uniform(50, 75), 1) if batt_cycles else None
        thermal      = random.randint(10, 22)        # ≥ policy threshold (10)
        smart        = random.randint(50, 110)       # ≥ policy threshold (50)
        perf_rating  = random.randint(1, 3)
        daily_hours  = round(random.uniform(8, 16), 1)
        usage_type   = random.choice(["Intensive", "Creative", "Development"])
        overheating  = thermal > 10
        data_comp    = round(random.uniform(0.75, 1.0), 2)

    elif rng < 0.70:  # Medium-risk → REFURBISH
        age          = random.randint(24, 48)
        incidents    = random.randint(3, 8)
        critical_inc = random.randint(0, 2)
        high_inc     = random.randint(1, 3)
        batt_cycles  = random.randint(200, 700) if device_type in ("Laptop", "Tablet", "Mobile Phone") else None
        batt_health  = round(random.uniform(65, 85), 1) if batt_cycles else None
        thermal      = random.randint(2, 8)
        smart        = random.randint(5, 40)
        perf_rating  = random.randint(2, 4)
        daily_hours  = round(random.uniform(4, 10), 1)
        usage_type   = random.choice(["Standard", "Development"])
        overheating  = thermal > 5
        data_comp    = round(random.uniform(0.60, 0.85), 2)

    elif rng < 0.90:  # Low-risk: young → REDEPLOY
        age          = random.randint(1, 23)
        incidents    = random.randint(0, 3)
        critical_inc = 0
        high_inc     = random.randint(0, 1)
        batt_cycles  = random.randint(0, 200) if device_type in ("Laptop", "Tablet", "Mobile Phone") else None
        batt_health  = round(random.uniform(88, 100), 1) if batt_cycles else None
        thermal      = random.randint(0, 2)
        smart        = random.randint(0, 5)
        perf_rating  = random.randint(4, 5)
        daily_hours  = round(random.uniform(4, 8), 1)
        usage_type   = random.choice(["Standard", "Light"])
        overheating  = False
        data_comp    = round(random.uniform(0.40, 0.70), 2)

    else:  # Low-risk: older but healthy → RESALE
        age          = random.randint(24, 42)
        incidents    = random.randint(0, 2)
        critical_inc = 0
        high_inc     = 0
        batt_cycles  = random.randint(100, 400) if device_type in ("Laptop", "Tablet", "Mobile Phone") else None
        batt_health  = round(random.uniform(80, 95), 1) if batt_cycles else None
        thermal      = random.randint(0, 3)
        smart        = random.randint(0, 10)
        perf_rating  = random.randint(3, 5)
        daily_hours  = round(random.uniform(3, 7), 1)
        usage_type   = random.choice(["Light", "Standard"])
        overheating  = False
        data_comp    = round(random.uniform(0.50, 0.80), 2)

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
        battery_health_pct=batt_health,
        thermal_events_count=thermal,
        smart_sectors_reallocated=smart,
        performance_rating=perf_rating,
        daily_usage_hours=daily_hours,
        usage_type=usage_type,
        overheating_issues=str(overheating),
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
        # Generate a realistic corporate serial number: <BRAND_PREFIX><YEAR><6_HEX>
        serial = f"{brand[:2].upper()}{year}{uuid.uuid4().hex[:6].upper()}"

        asset = AssetRow(
            asset_id=str(uuid.uuid4()),
            device_type=dtype,
            brand=brand,
            serial_number=serial,
            model_name=f"{brand} {dtype} {year}",
            model_year=year,
            department=dept,
            region=reg,
            os=os,
            age_months=profile["age_months"],
            usage_type=profile["usage_type"],
            daily_usage_hours=profile["daily_usage_hours"],
            performance_rating=profile["performance_rating"],
            battery_health_pct=profile["battery_health_pct"],
            overheating_issues=profile["overheating_issues"],
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
