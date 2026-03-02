# ML Model Dataset Creation Plan

## Overview

This document outlines the plan for creating the training dataset for the Intelligent E-Waste & Asset Lifecycle Optimizer ML model using existing public datasets.

---

## Available Data Sources

### Dataset 1: `laptop_battery_health_usage.csv` (50 laptops)

**Available fields:**
- `device_id` - Unique device identifier
- `brand` - Laptop manufacturer (HP, Dell, Apple, Lenovo, Asus, Acer)
- `model_year` - Year of manufacture (2018-2023)
- `os` - Operating system (Windows, macOS)
- `usage_type` - Usage category (Office, Programming, Creative, Student, Gaming)
- `daily_usage_hours` - Average hours of use per day
- `charging_cycles` - Total battery charge cycles
- `avg_charge_limit_percent` - Average charge limit percentage
- `battery_health_percent` - Current battery health percentage
- `battery_age_months` - Age of battery in months
- `overheating_issues` - Boolean flag (Yes/No)
- `performance_rating` - User performance rating (1-5 scale)

**Data quality:** 50 records with complete telemetry data

---

### Dataset 2: `expiry_price_data.csv` (1,235 laptops out of 15,000 total devices)

**Available fields:**
- `Product_Type` - Device category (Laptop, Smartphone, TV, etc.)
- `Brand` - Manufacturer (HP, Dell, Apple, Lenovo, Asus, Acer)
- `Build_Quality` - Quality rating (1-5 scale)
- `User_Lifespan` - Expected user lifespan in years
- `Usage_Pattern` - Usage intensity (Light, Moderate, Heavy)
- `Expiry_Years` - Estimated expiry years
- `Condition` - Current condition rating (1-5 scale)
- `Original_Price` - Purchase price in local currency
- `Used_Duration` - Duration of use in months
- `Current_Price` - Current market value

**Data quality:** 1,235 laptop records with pricing and lifecycle data

---

## ML Model Feature Requirements

Based on `data_requirements.md`, the ML model requires the following features:

### 1. Asset Metadata
- `age_in_months` (derived from `purchase_date`)
- `device_type` (laptop, server) - one-hot encoded
- `region` - categorical encoding
- `department` - categorical encoding

### 2. Telemetry Data
- `battery_cycles` (integer)
- `smart_sectors_reallocated` (integer)
- `thermal_events_count` (integer)

### 3. Ticket Aggregates (90-day window)
- `total_incidents` (integer)
- `critical_incidents` (integer)
- `high_incidents` (integer)
- `medium_incidents` (integer)
- `low_incidents` (integer)
- `avg_resolution_time_hours` (float)

### 4. Derived Features (engineered)
- Incident rate per month
- Critical incident ratio
- Battery degradation rate
- Thermal events per month of ownership

---

## Data Mapping Strategy

### ✅ Direct Mappings (Available)

| Required Field | Source Dataset | Source Field | Notes |
|----------------|----------------|--------------|-------|
| `battery_cycles` | Dataset 1 | `charging_cycles` | Direct mapping |
| `age_in_months` | Dataset 1 | `battery_age_months` | Direct mapping |
| `age_in_months` | Dataset 2 | `Used_Duration` | Alternative source |
| `device_type` | Both | Constant "laptop" | Prototype focuses on laptops |
| `brand` | Both | `brand` / `Brand` | Direct mapping |

### 🔧 Derived Mappings (Transformation Required)

| Required Field | Source | Derivation Logic |
|----------------|--------|------------------|
| `thermal_events_count` | Dataset 1 | Based on `overheating_issues` + age correlation |
| `smart_sectors_reallocated` | Dataset 1 | Synthetic, correlated with age and performance_rating |
| Ticket aggregates | Dataset 1 | Derived from `performance_rating`, `overheating_issues`, age |
| `purchase_date` | Dataset 1 | Calculate from `model_year` and `battery_age_months` |

### 📝 Synthetic Fields (Must Generate)

| Required Field | Generation Strategy |
|----------------|---------------------|
| `asset_id` | Generate sequential IDs (LAP-0001 to LAP-0050) |
| `region` | Random assignment (India, US, EU) with realistic distribution |
| `department` | Random assignment (Engineering, IT, Sales, HR, Finance, Operations) |
| `current_state` | Set to "Active" for prototype |

---

## Dataset Creation Approach

### Phase 1: Base Dataset from `laptop_battery_health_usage.csv`

**Objective:** Create 50 high-quality training records with complete feature coverage

**Steps:**

1. **Load base data** from `laptop_battery_health_usage.csv`

2. **Generate asset identifiers**
   - Format: `LAP-XXXX` (e.g., LAP-0001 to LAP-0050)
   - Ensure uniqueness

3. **Calculate temporal fields**
   - `purchase_date` = Current date - `battery_age_months`
   - `age_in_months` = `battery_age_months`

4. **Synthesize organizational context**
   - `department`: Weighted random (Engineering: 25%, IT: 20%, Sales: 20%, HR: 15%, Finance: 10%, Operations: 10%)
   - `region`: Weighted random (India: 40%, US: 35%, EU: 25%)

5. **Generate telemetry data**
   - `battery_cycles` = `charging_cycles` (direct)
   - `thermal_events_count`:
     - If `overheating_issues == "Yes"`: Random(10, 50) based on age
     - If `overheating_issues == "No"`: Random(0, 9)
   - `smart_sectors_reallocated`:
     - Base: Age-correlated (0-2 per month)
     - Boost if `performance_rating <= 2`: Add 20-50 sectors
     - Cap at 100 sectors

6. **Synthesize ticket aggregates**
   - Base incidents from `performance_rating`:
     - Rating 5: 0-2 incidents
     - Rating 4: 2-5 incidents
     - Rating 3: 5-8 incidents
     - Rating 2: 8-12 incidents
     - Rating 1: 12-20 incidents
   - Severity distribution:
     - Critical: 5% if overheating, 0% otherwise
     - High: 20% if overheating or performance <= 2
     - Medium: 40%
     - Low: Remainder
   - `avg_resolution_time_hours`: Random(4, 48) weighted by severity

7. **Calculate derived features**
   - Incident rate per month = `total_incidents / (age_in_months / 30 * 3)` (90-day window)
   - Critical incident ratio = `critical_incidents / total_incidents`
   - Battery degradation rate = `(100 - battery_health_percent) / age_in_months`
   - Thermal events per month = `thermal_events_count / age_in_months`

### Phase 2 (Optional): Expand with `expiry_price_data.csv`

**Objective:** Scale to 1,235 training records using laptop subset

**Additional synthesis required:**
- Map `Build_Quality` and `Condition` to `battery_health_percent`
- Map `Usage_Pattern` to `daily_usage_hours` and `charging_cycles`
- Estimate `overheating_issues` based on `Condition` and `Expiry_Years`
- Generate all missing telemetry and ticket fields using Phase 1 logic

---

## Data Quality Requirements

### Completeness Targets

Per design document requirements:
- **Data completeness ≥ 0.6** for at least 70% of assets
- All required ML model features must be populated
- Missing optional fields acceptable but should be flagged

### Validation Rules

1. **Temporal consistency**
   - `age_in_months` must be positive
   - `purchase_date` must be before current date
   - `battery_age_months` <= `age_in_months`

2. **Value ranges**
   - `battery_health_percent`: 0-100
   - `performance_rating`: 1-5
   - `risk_score`: 0.0-1.0 (when labeled)
   - `smart_sectors_reallocated`: 0-100
   - `thermal_events_count`: >= 0

3. **Logical consistency**
   - High `thermal_events_count` should correlate with `overheating_issues == "Yes"`
   - Low `performance_rating` should correlate with higher incident counts
   - Older devices should show more degradation signals

### Synthetic Data Realism

To ensure synthetic fields don't bias the model:
- Use realistic distributions based on domain knowledge
- Introduce correlation patterns matching real-world behavior
- Add appropriate noise to avoid perfect correlations
- Validate against policy engine thresholds for sanity checks

---

## Target Label Generation

For supervised learning, we need to create target labels indicating asset risk/failure.

### Labeling Strategy

**High Risk (Label = 1)** if any of:
- `battery_health_percent < 70`
- `performance_rating <= 2`
- `thermal_events_count >= 10`
- `smart_sectors_reallocated >= 50`
- `age_in_months >= 42 AND total_incidents >= 5`

**Medium Risk (Label = 0.5)** if:
- Partial criteria met
- `battery_health_percent` 70-85
- `performance_rating == 3`

**Low Risk (Label = 0)** otherwise

### Alternative: Regression Target

Instead of classification, use continuous risk score:
```
risk_score = weighted_average(
    battery_degradation_score: 0.25,
    thermal_risk_score: 0.20,
    disk_health_score: 0.20,
    incident_score: 0.20,
    age_score: 0.15
)
```

---

## Output Schema

### Final Training Dataset Schema

```csv
asset_id,purchase_date,device_type,department,region,brand,model_year,age_in_months,
battery_cycles,battery_health_percent,smart_sectors_reallocated,thermal_events_count,
total_incidents,critical_incidents,high_incidents,medium_incidents,low_incidents,
avg_resolution_time_hours,daily_usage_hours,usage_type,os,overheating_issues,
performance_rating,incident_rate_per_month,critical_incident_ratio,
battery_degradation_rate,thermal_events_per_month,risk_score,risk_label
```

### Data Files to Generate

1. **`training_data.csv`** - Complete training dataset with all features and labels
2. **`asset_metadata.csv`** - Asset master data (for Asset table)
3. **`telemetry_data.csv`** - Telemetry readings (for Telemetry table)
4. **`tickets_aggregate.csv`** - Ticket summaries (for TicketsAggregate table)
5. **`data_quality_report.md`** - Validation report with completeness scores

---

## Implementation Plan

### Step 1: Data Generation Script
Create Python script `generate_training_data.py` to:
- Load source CSV files
- Apply transformation and synthesis logic
- Generate all required fields
- Validate data quality
- Export formatted datasets

### Step 2: Validation
- Run data quality checks
- Verify distributions and correlations
- Validate against policy engine rules
- Generate completeness report

### Step 3: Model Training Preparation
- Split data: 70% train, 15% validation, 15% test
- Feature scaling/normalization as needed
- Document feature engineering steps

---

## Success Criteria

✅ **Minimum viable dataset:**
- 50 records with complete features
- Data completeness ≥ 0.6 for 100% of records
- All required ML model features populated
- Realistic correlations between features
- Balanced risk label distribution (30-40% high risk)

✅ **Quality validation:**
- Pass all temporal consistency checks
- Pass all value range validations
- Logical consistency verified
- No missing critical fields

✅ **Model readiness:**
- Features match ML model input schema
- Target labels generated using documented logic
- Train/validation/test splits created
- Feature documentation complete

---

## Phased Implementation Plan

### Phase 1: Foundation Setup (Week 1)

**Objective:** Establish data generation infrastructure and create initial 50-record dataset

#### Tasks:

1. **Environment Setup**
   - Create `src/data_generation/` directory structure
   - Set up Python environment with required packages:
     - `pandas` for data manipulation
     - `numpy` for numerical operations
     - `faker` for synthetic data generation
     - `datetime` for temporal calculations
   - Create configuration file `data_generation_config.yaml`

2. **Script Development: `generate_training_data.py`**
   - Implement CSV loader for `laptop_battery_health_usage.csv`
   - Create data model classes matching ML feature schema
   - Implement validation functions for data quality checks

3. **Core Transformations (Batch 1)**
   - Asset ID generation (LAP-0001 format)
   - Temporal field calculations (purchase_date, age_in_months)
   - Direct mappings (battery_cycles, brand, model_year)

4. **Testing & Validation**
   - Unit tests for transformation functions
   - Data quality validation checks
   - Generate first 10 records as proof of concept

**Deliverables:**
- ✅ Working `generate_training_data.py` script (basic version)
- ✅ 10 validated records with core features
- ✅ Data quality validation framework

---

### Phase 2: Synthetic Data Generation (Week 2)

**Objective:** Implement all synthetic field generation logic with realistic distributions

#### Tasks:

1. **Organizational Context Generator**
   - Department assignment with weighted distribution
   - Region assignment with compliance considerations
   - Document assignment logic and weights

2. **Telemetry Synthesis Module**
   - `thermal_events_count` generator:
     - Correlation with `overheating_issues` flag
     - Age-based distribution logic
     - Add realistic noise
   - `smart_sectors_reallocated` generator:
     - Age-based degradation curve
     - Performance rating correlation
     - Implement 0-100 cap

3. **Ticket Aggregate Synthesis Module**
   - Incident count generator based on performance_rating
   - Severity distribution calculator
   - Resolution time estimator
   - Implement 90-day window logic

4. **Feature Engineering Pipeline**
   - Incident rate per month calculation
   - Critical incident ratio computation
   - Battery degradation rate derivation
   - Thermal events per month calculation

5. **Testing & Refinement**
   - Validate correlations between synthetic and real fields
   - Check for unrealistic patterns
   - Verify policy engine alignment

**Deliverables:**
- ✅ Complete 50-record dataset with all features
- ✅ Correlation analysis report
- ✅ `asset_metadata.csv`, `telemetry_data.csv`, `tickets_aggregate.csv`

---

### Phase 3: Target Label Generation & Validation (Week 3)

**Objective:** Create risk labels and validate dataset quality for ML training

#### Tasks:

1. **Risk Label Generator**
   - Implement policy-based labeling logic
   - Create continuous risk score calculator
   - Generate classification labels (High/Medium/Low)
   - Document labeling criteria

2. **Data Quality Assurance**
   - Run completeness checks (target: ≥0.6 for 100%)
   - Validate temporal consistency
   - Check value range compliance
   - Verify logical consistency rules

3. **Statistical Analysis**
   - Distribution analysis for all features
   - Risk label distribution (target: 30-40% high risk)
   - Correlation matrix generation
   - Outlier detection and handling

4. **Documentation**
   - Generate `data_quality_report.md`
   - Document all synthetic data assumptions
   - Create feature dictionary
   - Write data generation methodology document

**Deliverables:**
- ✅ `training_data.csv` with risk labels (50 records)
- ✅ `data_quality_report.md` with validation results
- ✅ Feature distribution visualizations
- ✅ Complete data dictionary

---

### Phase 4: Dataset Expansion Preparation (Week 4)

**Objective:** Prepare for scaling to 1,235 records using expiry_price_data.csv

#### Tasks:

1. **Expiry Price Data Analysis**
   - Extract 1,235 laptop records
   - Map fields to existing schema
   - Identify data quality issues
   - Create field transformation rules

2. **Extended Synthesis Module**
   - Build Quality → battery_health_percent mapping
   - Condition → performance_rating translation
   - Usage_Pattern → daily_usage_hours/charging_cycles conversion
   - Expiry_Years → age and degradation signals

3. **Integration Pipeline**
   - Merge logic for combining Dataset 1 and Dataset 2
   - Deduplication strategy (if needed)
   - Maintain data provenance tags
   - Ensure consistent feature distributions

4. **Validation Framework Extension**
   - Scale validation checks to handle 1,200+ records
   - Cross-dataset consistency checks
   - Performance optimization for large datasets

**Deliverables:**
- ✅ `generate_extended_dataset.py` script
- ✅ Field mapping specification document
- ✅ 100-record pilot from expiry_price_data
- ✅ Integration validation report

---

### Phase 5: Full Dataset Generation & Model Preparation (Week 5)

**Objective:** Generate complete 1,235-record dataset and prepare for ML training

#### Tasks:

1. **Full Dataset Generation**
   - Run extended generation pipeline
   - Generate all 1,235 records with complete features
   - Apply quality filters (remove low-quality records if needed)
   - Create final `training_data_full.csv`

2. **Train/Validation/Test Split**
   - 70% training set (~865 records)
   - 15% validation set (~185 records)
   - 15% test set (~185 records)
   - Stratified split to maintain risk label distribution
   - Document split methodology

3. **Feature Preprocessing**
   - One-hot encoding for categorical variables
   - Feature scaling/normalization specification
   - Missing value handling strategy (if any)
   - Create preprocessing pipeline documentation

4. **Model Training Data Package**
   - `train.csv`, `validation.csv`, `test.csv`
   - `feature_config.json` (encoding, scaling parameters)
   - `preprocessing_pipeline.py` script
   - Model input schema documentation

5. **Final Quality Gate**
   - Run comprehensive validation suite
   - Generate final data quality metrics
   - Peer review of synthetic data logic
   - Sign-off on dataset readiness

**Deliverables:**
- ✅ Complete 1,235-record dataset with quality validation
- ✅ Train/validation/test splits
- ✅ Preprocessing pipeline and configuration
- ✅ Final data package for ML team
- ✅ Dataset generation documentation

---

### Phase 6: Continuous Improvement & Maintenance (Ongoing)

**Objective:** Iterate based on model performance and collect real-world data

#### Tasks:

1. **Model Feedback Integration**
   - Analyze initial model performance (AUC-ROC target: ≥0.70)
   - Identify problematic features or distributions
   - Refine synthetic data generation logic
   - Re-generate dataset if needed

2. **Real Data Collection Planning**
   - Define data ingestion API schema
   - Plan gradual replacement of synthetic with real data
   - Maintain data provenance tracking
   - Establish data quality monitoring

3. **Dataset Versioning**
   - Implement semantic versioning (v1.0, v1.1, etc.)
   - Track changes between versions
   - Maintain backward compatibility
   - Document dataset evolution

4. **Benchmark Dataset Maintenance**
   - Keep test set stable for model comparison
   - Update training set as real data arrives
   - Re-balance labels if distribution shifts
   - Annual dataset refresh strategy

**Deliverables:**
- ✅ Dataset version control system
- ✅ Real data integration pipeline (design)
- ✅ Performance feedback loop
- ✅ Long-term data strategy document

---

## Timeline Summary

| Phase | Duration | Key Milestone | Dependencies |
|-------|----------|---------------|--------------|
| Phase 1 | Week 1 | 10-record POC | Environment setup |
| Phase 2 | Week 2 | 50-record complete dataset | Phase 1 |
| Phase 3 | Week 3 | Validated training data | Phase 2 |
| Phase 4 | Week 4 | Expansion pipeline ready | Phase 3 |
| Phase 5 | Week 5 | Full 1,235-record dataset | Phase 4 |
| Phase 6 | Ongoing | Model integration | Phase 5 |

**Total Initial Development: 5 weeks**

---

## Risk Mitigation

### Risk 1: Synthetic Data Bias
**Mitigation:** 
- Validate against policy engine rules
- Use domain expert review
- Compare distributions with known industry benchmarks
- Plan early transition to real data

### Risk 2: Insufficient Feature Correlation
**Mitigation:**
- Implement correlation validation in each phase
- Use research-backed degradation models
- Adjust weights based on real-world patterns
- Document assumptions for transparency

### Risk 3: Dataset Quality Below Threshold
**Mitigation:**
- Incremental validation at each phase
- Quality gates before proceeding to next phase
- Buffer time for refinement iterations
- Maintain fallback to smaller high-quality dataset

### Risk 4: Model Performance Below Target (AUC-ROC < 0.70)
**Mitigation:**
- Baseline with logistic regression first
- Feature engineering iteration budget
- Consider ensemble methods
- Re-evaluate feature selection based on importance

---

## Resource Requirements

### Technical Resources
- Python 3.9+ environment
- 8GB RAM for data generation
- 50GB storage for datasets and iterations
- Git repository for version control

### Human Resources
- Data Engineer: 40 hours (Phases 1-2)
- ML Engineer: 20 hours (Phases 3, 5)
- Domain Expert: 10 hours (validation, review)
- QA Engineer: 10 hours (testing, validation)

### Infrastructure
- Development environment (local or cloud)
- Data storage (S3 or equivalent)
- CI/CD pipeline for automated validation
- Monitoring dashboard for data quality metrics

---

## Success Metrics

### Phase Completion Criteria

**Phase 1:**
- [ ] 10 records generated with 100% completeness
- [ ] All core transformations tested and validated
- [ ] Zero critical validation errors

**Phase 2:**
- [ ] 50 records with all features populated
- [ ] Data completeness ≥ 0.6 for 100% of records
- [ ] Correlation checks pass for synthetic-real field pairs

**Phase 3:**
- [ ] Risk labels distributed 30-40% high risk
- [ ] Data quality report shows green status
- [ ] All validation rules pass

**Phase 4:**
- [ ] 100-record pilot from expiry data validates successfully
- [ ] Field mappings documented and reviewed
- [ ] Integration pipeline tested

**Phase 5:**
- [ ] 1,235 records generated and validated
- [ ] Train/val/test splits created with proper stratification
- [ ] ML team confirms data package readiness

**Phase 6:**
- [ ] Model achieves AUC-ROC ≥ 0.70
- [ ] Real data integration pipeline designed
- [ ] Dataset versioning system operational

---

## Next Immediate Actions

1. **Week 1, Day 1-2:** Set up project structure and environment
2. **Week 1, Day 3-5:** Implement Phase 1 core transformations
3. **Week 2, Day 1-3:** Build synthetic data generators
4. **Week 2, Day 4-5:** Generate and validate 50-record dataset
5. **Week 3:** Quality validation and risk labeling
