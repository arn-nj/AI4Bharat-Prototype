# Model Training — E-Waste Asset Lifecycle Optimizer

This folder contains everything needed to train, evaluate, and persist the **risk label classifier** that predicts whether an IT asset is at `low`, `medium`, or `high` end-of-life risk.

---

## Folder Contents

| File / Folder | Description |
|---|---|
| `train_model.py` | Main training script — preprocessing → model training → evaluation → artifact export |
| `training_data_phase5_1235records_fixed.csv` | Quality-verified training dataset (1,235 records) |
| `data_statistics_summary.csv` | Descriptive statistics (mean, std, percentiles) for all numeric fields |
| `feature_correlations.csv` | Pairwise Pearson correlation matrix across numeric features |
| `data_analysis.ipynb` | Exploratory data analysis notebook |
| `data_quality_verification.ipynb` | Data quality checks and validation notebook |
| `model_inference_testing.ipynb` | Notebook for running inference tests against the saved model |
| `models/risk_label_model.joblib` | Saved best model (sklearn Pipeline: preprocessor + classifier) |
| `models/model_metadata.json` | Training configuration, feature lists, label encoding, and evaluation metrics |
| `models/plots/evaluation.png` | Confusion matrix, per-class F1-score, and feature importance chart |
| `models/plots/model_comparison.png` | CV vs. validation AUC-ROC comparison across candidate models |

---

## Dataset Fields

The training dataset (`training_data_phase5_1235records_fixed.csv`) has **32 columns** per record.

### Identifiers & Dates

| Field | Type | Description |
|---|---|---|
| `asset_id` | string | Unique asset identifier (e.g. `LAP-0001`) |
| `purchase_date` | datetime | Date the asset was purchased |
| `created_at` | datetime | Timestamp when the record was generated |

### Device Properties

| Field | Type | Description |
|---|---|---|
| `device_type` | categorical | Type of device — `laptop`, `desktop`, `tablet`, etc. |
| `brand` | categorical | Manufacturer — e.g. `HP`, `Dell`, `Apple`, `Lenovo`, `Asus`, `Acer` |
| `model_year` | integer | Year the device model was released (2018–2026) |
| `department` | categorical | Business unit that owns the asset — e.g. `Engineering`, `Finance`, `HR`, `IT`, `Sales` |
| `region` | categorical | Geographic region — `US`, `EU`, `India` |
| `usage_type` | categorical | Primary use pattern — `Office`, `Programming`, `Gaming`, `Creative`, `Student` |
| `os` | categorical | Operating system — `Windows`, `macOS` |

### Age & Battery Health

| Field | Type | Description |
|---|---|---|
| `age_in_months` | integer | Age of the asset in calendar months (1–72) |
| `purchase_year` | integer | Year extracted from `purchase_date`; used for verification only, excluded from training |
| `age_in_months_recalc` | integer | Recomputed age from `purchase_date`; used for quality checks, excluded from training |
| `battery_cycles` | integer | Total number of charge–discharge cycles completed (100–950) |
| `battery_health_percent` | float | Remaining battery capacity as a percentage of original (40–98%) |
| `battery_degradation_rate` | float | Rate of capacity loss per month (higher = faster decline) |
| `overheating_issues` | boolean | Whether the device has a history of overheating (`True` / `False`) |

### Storage Health

| Field | Type | Description |
|---|---|---|
| `smart_sectors_reallocated` | integer | Number of reallocated sectors reported by S.M.A.R.T. diagnostics (0–100); higher indicates storage wear |

### Thermal Metrics

| Field | Type | Description |
|---|---|---|
| `thermal_events_count` | integer | Total number of thermal (overheating) events recorded (0–50) |
| `thermal_events_per_month` | float | Normalised thermal event rate per calendar month |

### Usage & Performance

| Field | Type | Description |
|---|---|---|
| `daily_usage_hours` | float | Average hours the device is actively used per day (3–12) |
| `performance_rating` | integer | Benchmark-derived performance rating on a 1–5 scale (1 = poor, 5 = excellent) |

### Incident Metrics

| Field | Type | Description |
|---|---|---|
| `total_incidents` | integer | Total IT support tickets raised for the asset (0–20) |
| `critical_incidents` | integer | Support tickets classified as critical severity (0–4) |
| `high_incidents` | integer | Support tickets classified as high severity (0–4) |
| `medium_incidents` | integer | Support tickets classified as medium severity (0–8) |
| `low_incidents` | integer | Support tickets classified as low severity (0–9) |
| `avg_resolution_time_hours` | float | Average number of hours to close an incident (0–13.14) |
| `incident_rate_per_month` | float | Total incidents divided by age in months |
| `critical_incident_ratio` | float | Fraction of incidents that are critical (0–0.05) |

### Risk Scoring

| Field | Type | Description |
|---|---|---|
| `risk_score` | float | Composite numeric risk score (0.05–0.72); **excluded from training to prevent leakage** |
| `risk_label` | categorical | **Target variable** — discretised risk class: `low` (score < 0.35), `medium` (0.35–0.55), `high` (≥ 0.55) |

### Data Quality

| Field | Type | Description |
|---|---|---|
| `data_completeness` | float | Fraction of expected fields that are populated (0–1); 1.0 = fully complete record |

---

## Model Training

### Goal

Predict `risk_label` (`low` / `medium` / `high`) for any IT asset from operational telemetry and support ticket data. The primary success criterion is **AUC-ROC ≥ 0.70** (macro one-vs-rest).

### Feature Engineering

`train_model.py` excludes the following columns before training:

- **Identifiers / raw dates** — `asset_id`, `purchase_date`, `created_at`
- **Leakage** — `risk_score` (directly encodes the target label)
- **Verification artefacts** — `purchase_year`, `age_in_months_recalc`
- **Target** — `risk_label`

The remaining 26 features split into:

- **19 numeric features** — `model_year`, `age_in_months`, `battery_cycles`, `battery_health_percent`, `smart_sectors_reallocated`, `thermal_events_count`, `daily_usage_hours`, `performance_rating`, `total_incidents`, `critical_incidents`, `high_incidents`, `medium_incidents`, `low_incidents`, `avg_resolution_time_hours`, `incident_rate_per_month`, `critical_incident_ratio`, `battery_degradation_rate`, `thermal_events_per_month`, `data_completeness`
- **7 categorical features** — `device_type`, `brand`, `department`, `region`, `usage_type`, `os`, `overheating_issues`

### Preprocessing Pipeline

```
ColumnTransformer
├── StandardScaler          → numeric features
└── OneHotEncoder           → categorical features (handle_unknown="ignore")
```

### Data Split

| Subset | Fraction | Size (approx.) |
|---|---|---|
| Train | 70% | 864 records |
| Validation | 15% | 185 records |
| Test | 15% | 186 records |

All splits are **stratified** on `risk_label` to preserve class proportions.

### Candidate Models

| Model | Configuration |
|---|---|
| **Logistic Regression** (baseline) | `C=1.0`, `class_weight="balanced"`, `max_iter=1000` |
| **Gradient Boosting** | `n_estimators=200`, `learning_rate=0.1`, `max_depth=4`, `subsample=0.8`, `min_samples_leaf=10` |

Each model is evaluated with **5-fold stratified cross-validation** on the combined train+validation set, then fitted on the training split and scored on the validation split to select the best model.

### Best Model & Metrics

The **Logistic Regression** classifier was selected (highest validation AUC-ROC).

| Metric | Value |
|---|---|
| Test Accuracy | **94.62%** |
| Test AUC-ROC (macro OvR) | **0.9962** ✓ |
| Validation Accuracy | 97.31% |
| Validation AUC-ROC | 0.9990 |

**Per-class test performance:**

| Class | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| `high` | 0.9437 | 0.9710 | 0.9571 | 69 |
| `low` | 0.9756 | 0.9302 | 0.9524 | 43 |
| `medium` | 0.9324 | 0.9324 | 0.9324 | 74 |

### Artifacts Produced

| Artifact | Path | Description |
|---|---|---|
| Trained pipeline | `models/risk_label_model.joblib` | Sklearn Pipeline (preprocessor + classifier) with `LabelEncoder` bundled |
| Metadata | `models/model_metadata.json` | Feature lists, label encoding, thresholds, and all evaluation metrics |
| Evaluation plots | `models/plots/evaluation.png` | Confusion matrix, per-class F1, feature importances |
| Comparison plot | `models/plots/model_comparison.png` | CV vs. validation AUC-ROC bar chart |

### Running Training

```bash
cd src/model_training
python train_model.py
```

---

## 10 Example Records

The following are the first 10 records from the training dataset, illustrating the range of device conditions and resulting risk labels.

### Record 1 — `LAP-0001` · High Risk

```
Device:      HP Laptop, Engineering dept, US region
Age:         75 months  |  Battery: 420 cycles, 35% health
SMART:       73 reallocated sectors  |  Thermal events: 39
Performance: 3/5  |  Total incidents: 16  (4 critical, 5 high)
Risk score:  0.775  →  risk_label: HIGH
```

**Why high?** The device is over 6 years old with critically degraded battery health (35%), extensive storage wear (73 SMART sectors), near-200% the average thermal event rate, and 4 critical support incidents. Every hardware signal points to imminent failure.

---

### Record 2 — `LAP-0002` · Medium Risk

```
Device:      Dell Laptop, Engineering dept, India region
Age:         58 months  |  Battery: 610 cycles, 78% health
SMART:       91 reallocated sectors  |  Thermal events: 24
Performance: 3/5  |  Total incidents: 6  (0 critical, 1 high)
Risk score:  0.514  →  risk_label: MEDIUM
```

**Why medium?** SMART sectors are high (91) and overheating is flagged, but battery health is reasonable at 78% with zero critical incidents. The composite risk score lands in the medium band (0.35–0.55).

---

### Record 3 — `LAP-0003` · Low Risk

```
Device:      Apple Laptop, Finance dept, India region
Age:         31 months  |  Battery: 310 cycles, 92% health
SMART:       56 reallocated sectors  |  Thermal events: 2
Performance: 5/5  |  Total incidents: 1  (0 critical)
Risk score:  0.215  →  risk_label: LOW
```

**Why low?** Excellent battery health (92%), very few thermal events (2), top performance rating (5/5), and only one minor incident in 31 months. Classic healthy mid-life asset.

---

### Record 4 — `LAP-0004` · Medium Risk

```
Device:      Lenovo Laptop, Engineering dept, EU region
Age:         7 months  |  Battery: 700 cycles, 70% health
SMART:       100 reallocated sectors  |  Thermal events: 48
Performance: 3/5  |  Total incidents: 5  (0 critical, 1 high)
Risk score:  0.532  →  risk_label: MEDIUM
```

**Why medium?** Despite being only 7 months old, this asset has maxed-out SMART sectors (100) and extremely high thermal events (48) with overheating flagged — likely defective hardware. Battery degradation rate (4.29%/month) is elevated. Risk is real but no critical incidents yet pushes it to medium rather than high.

---

### Record 5 — `LAP-0005` · High Risk

```
Device:      Asus Laptop, IT dept, US region
Age:         31 months  |  Battery: 820 cycles, 65% health
SMART:       100 reallocated sectors  |  Thermal events: 33
Performance: 2/5  |  Total incidents: 8  (0 critical, 1 high)
Risk score:  0.564  →  risk_label: HIGH
```

**Why high?** Maxed-out SMART sectors, low performance (2/5), heavy gaming usage pushing 820 battery cycles in just 31 months, and persistent overheating. Data completeness is only 66%, indicating missing telemetry — itself a reliability signal.

---

### Record 6 — `LAP-0006` · High Risk

```
Device:      Acer Laptop, Finance dept, India region
Age:         74 months  |  Battery: 540 cycles, 34% health
SMART:       93 reallocated sectors  |  Thermal events: 49
Performance: 2/5  |  Total incidents: 19  (4 critical, 5 high)
Risk score:  0.887  →  risk_label: HIGH
```

**Why high?** One of the highest-risk records in the dataset. Battery health at 34%, the most thermal events (49) in this sample, 4 critical incidents, and a 6-year age. Risk score of 0.887 is well into the high band.

---

### Record 7 — `LAP-0007` · High Risk

```
Device:      Apple Laptop, Engineering dept, US region
Age:         76 months  |  Battery: 210 cycles, 18% health
SMART:       92 reallocated sectors  |  Thermal events: 45
Performance: 2/5  |  Total incidents: 18  (3 critical, 5 high)
Risk score:  0.899  →  risk_label: HIGH
```

**Why high?** Battery health at just 18% is the lowest in this sample, combined with 76 months age, 45 thermal events, 3 critical incidents, and near-failure SMART reading. Highest individual risk score (0.899) in the first 10 rows.

---

### Record 8 — `LAP-0008` · High Risk

```
Device:      HP Laptop, HR dept, EU region
Age:         81 months  |  Battery: 880 cycles, 25% health
SMART:       90 reallocated sectors  |  Thermal events: 45
Performance: 1/5  |  Total incidents: 19  (4 critical, 6 high)
Risk score:  0.888  →  risk_label: HIGH
```

**Why high?** The oldest asset in sample at 81 months, worst performance rating (1/5), 880 cycles, 25% battery health, 90 SMART sectors, and 4 critical incidents. A clear replacement candidate.

---

### Record 9 — `LAP-0009` · Low Risk

```
Device:      Dell Laptop, Finance dept, India region
Age:         30 months  |  Battery: 350 cycles, 88% health
SMART:       67 reallocated sectors  |  Thermal events: 7
Performance: 4/5  |  Total incidents: 5  (0 critical)
Risk score:  0.304  →  risk_label: LOW
```

**Why low?** Good battery health (88%), low thermal events, solid performance (4/5), and no critical or high-severity incidents. Despite moderate SMART sectors, the overall telemetry profile is healthy.

---

### Record 10 — `LAP-0010` · Low Risk

```
Device:      Lenovo Laptop, Sales dept, EU region
Age:         7 months  |  Battery: 480 cycles, 83% health
SMART:       78 reallocated sectors  |  Thermal events: 6
Performance: 4/5  |  Total incidents: 3  (0 critical)
Risk score:  0.267  →  risk_label: LOW
```

**Why low?** Only 7 months old, good battery (83%), strong performance (4/5), few incidents, no overheating — a near-new asset in healthy condition. The risk score of 0.267 reflects minimal operational concern.

---

## Key Feature Correlations

Based on `feature_correlations.csv`, the strongest signals for the model are:

| Feature Pair | Correlation | Intuition |
|---|---|---|
| `performance_rating` ↔ `battery_health_percent` | **+0.91** | Healthier batteries = better performance |
| `performance_rating` ↔ `total_incidents` | **-0.92** | More incidents = lower performance |
| `total_incidents` ↔ `incident_rate_per_month` | **+1.00** | Near-identical signals (normalised version) |
| `smart_sectors_reallocated` ↔ `total_incidents` | **+0.72** | Disk wear correlates with support tickets |
| `battery_degradation_rate` ↔ `thermal_events_per_month` | **+0.58** | Overheating accelerates battery decay |
| `age_in_months` ↔ `battery_cycles` | **+0.92** | Older devices have more charge cycles |
