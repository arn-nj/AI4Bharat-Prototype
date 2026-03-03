# Intelligent E-Waste & Asset Lifecycle Optimizer

A decision-support system that combines **ML risk scoring**, **deterministic policy rules**, and **Amazon Bedrock LLM** to recommend lifecycle actions (Redeploy / Repair / Refurbish / Resale / Recycle) for IT assets.

| Environment | Frontend | API |
|---|---|---|
| **Production** | https://d1mf9ava5cnnbs.cloudfront.net | https://jh4ppmtagk.execute-api.us-east-1.amazonaws.com/prod |
| **Dev** | https://d38pk4y15auu3k.cloudfront.net | https://pacyjst474.execute-api.us-east-1.amazonaws.com/dev |

---

## Architecture

```
src/
├── backend/            FastAPI — ML + Policy + LLM pipeline (Lambda container)
├── frontend/           React 18 + Vite 5 + Tailwind — static site on S3+CloudFront
├── llm_engine/         Amazon Bedrock client + prompt builders
├── model_training/     Training data, Jupyter notebooks, trained model artifacts
└── storage/            S3 helper (model artifacts, compliance docs)

scripts/
├── deploy.sh           Full-stack local deploy (sam build → SAM deploy → npm build → S3 sync)
└── start.ps1           Local dev launcher (FastAPI + Vite dev server)
```

**AWS stack:**

```
Browser → CloudFront → S3 (React build)
Browser → API Gateway → Lambda (FastAPI/Mangum) → Amazon Bedrock
                                                 → S3 (model artifacts)
```

---

## Folder structure

```
.
├── Dockerfile                    Lambda container image for the backend
├── template.yaml                 AWS SAM template (Lambda + API GW + S3 + CloudFront)
├── samconfig.toml                SAM deploy defaults
├── requirements.txt              Python dependencies (backend + training)
├── .github/
│   └── workflows/ci-cd.yaml     GitHub Actions: lint → deploy-dev / deploy-prod
├── scripts/
│   ├── deploy.sh                 One-command full-stack deploy script
│   ├── start.ps1                 Local dev launcher (Windows)
│   └── upload_models_to_s3.py   Standalone model artifact uploader
├── src/
│   ├── backend/
│   │   ├── main.py               FastAPI app, routes, CORS, Mangum handler
│   │   ├── models.py             Pydantic request/response schemas
│   │   ├── device_analyser.py    Pipeline orchestrator: ML → Policy → LLM
│   │   └── test_analyse_device.py  10-scenario integration test script
│   ├── frontend/
│   │   ├── src/                  React components + API client
│   │   ├── vite.config.ts
│   │   └── package.json
│   ├── llm_engine/
│   │   ├── llm.py                Amazon Bedrock client + four caller methods
│   │   └── prompts.py            Prompt builders + fallback templates
│   ├── model_training/
│   │   ├── train_model.py        Gradient boosting model training
│   │   ├── models/               model artifacts (joblib + metadata JSON)
│   │   └── *.ipynb               EDA, data quality, inference testing notebooks
│   └── storage/
│       └── s3_storage.py         S3 get/put helpers
└── documents/
    ├── requirements.md
    ├── design.md
    └── ...
```

---

## Local development

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.12 |
| Node.js | 20 |
| Docker | any recent |
| AWS SAM CLI | latest |
| AWS credentials | configured (`aws configure` or env vars) |

### 1 — Python virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\Activate.ps1
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 2 — Train the ML model (first time only)

```bash
python src/model_training/train_model.py
```

Produces two files used at runtime:

| File | Path |
|---|---|
| `risk_label_model.joblib` | `src/model_training/models/` |
| `model_metadata.json` | `src/model_training/models/` |

### 3 — Environment variables

Create a `.env` file at the repo root:

```bash
# Amazon Bedrock (required for LLM stage)
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=qwen.qwen3-30b-a3b

# S3 bucket for model artifacts (optional — falls back to local files)
S3_BUCKET_NAME=ewaste-asset-optimizer-dev-992332682921
```

> If Bedrock credentials are missing the pipeline falls back to deterministic templates — ML + Policy stages continue to work normally.

### 4 — Start the full local stack

```powershell
# Windows — opens two terminal windows
.\scripts\start.ps1

# Custom ports
.\scripts\start.ps1 -Port 9000 -FrontendPort 5174
```

| Service | Default URL |
|---|---|
| FastAPI backend | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| React frontend (Vite) | http://localhost:5173 |

**Or start manually:**

```bash
# Backend
cd src/backend && uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd src/frontend && VITE_BACKEND_URL=http://localhost:8000 npm run dev
```

---

## API reference

### `GET /health`

```json
{ "status": "ok", "service": "asset-lifecycle-optimizer" }
```

### `GET /model_info`

Returns ML model metadata: version, training date, AUC-ROC, feature list.

### `POST /analyse_device`

Runs the full 4-stage pipeline and returns a complete analysis.

**Pipeline stages:**

| # | Stage | Module | Description |
|---|---|---|---|
| 1 | Feature engineering | `device_analyser.py` | Derives rates: `incident_rate_per_month`, `critical_incident_ratio`, `battery_degradation_rate`, `thermal_events_per_month` |
| 2 | ML inference | `device_analyser.py` | Gradient boosting predicts `high`/`medium`/`low` + class probabilities. Skipped when `data_completeness < 0.6`. |
| 3 | Policy engine | `device_analyser.py` | Deterministic threshold rules map risk to lifecycle action |
| 4 | LLM engine | `llm_engine/llm.py` | Bedrock generates ≤120-word explanation + structured ITSM task JSON. Falls back to templates on timeout. |

**Policy rules:**

| Rule | Condition | Classification |
|---|---|---|
| `age_and_tickets` | `age ≥ 42 months AND total_incidents ≥ 5` | High |
| `thermal_threshold` | `thermal_events_count ≥ 10` | High |
| `smart_sectors_threshold` | `smart_sectors_reallocated ≥ 50` | High |
| *(partial)* | `age ≥ 30 AND tickets ≥ 3` OR `thermal ≥ 5` OR `smart ≥ 25` | Medium |

**Action mapping:**

| Condition | Action |
|---|---|
| `risk_score ≥ 0.80` AND `age ≥ 42 months` | `RECYCLE` |
| `risk_score ≥ 0.70` AND device is repairable | `REPAIR` |
| `risk_score ≥ 0.50` | `REFURBISH` |
| `risk_score < 0.30` | `REDEPLOY` |
| else | `RESALE` |

**Request fields (`DeviceInput`):**

| Field | Type | Description |
|---|---|---|
| `asset_id` | `str` | Unique asset identifier |
| `device_type` | `str` | `Laptop` \| `Server` \| `Desktop` |
| `brand`, `department`, `region` | `str` | Asset metadata |
| `age_in_months` | `int ≥ 0` | Asset age |
| `battery_health_percent` | `float 0–100` | Current battery health |
| `battery_cycles` | `int ≥ 0` | Charge cycles |
| `smart_sectors_reallocated` | `int ≥ 0` | SMART drive indicator |
| `thermal_events_count` | `int ≥ 0` | Overheating events (90-day window) |
| `total_incidents` | `int ≥ 0` | Support tickets (90-day window) |
| `critical_incidents` | `int ≥ 0` | P1 tickets |
| `performance_rating` | `int 1–5` | Subjective performance score |
| `data_completeness` | `float 0–1` | Below `0.6` → policy-only path |

**Response fields (`AnalysisResult`):**

| Field | Description |
|---|---|
| `final_action` | Lifecycle action: `RECYCLE` / `REPAIR` / `REFURBISH` / `RESALE` / `REDEPLOY` |
| `confidence_score` | Max ML class probability, or `0.5` on policy-only path |
| `ml_result` | Risk label, score, confidence band, class probabilities |
| `policy_result` | Classification, triggered rules, supporting signals |
| `llm_result` | Explanation text, ITSM task JSON, `llm_available` flag |

### Integration test

Runs 10 hand-crafted scenarios against the live API:

```bash
cd src/backend
python test_analyse_device.py
python test_analyse_device.py --url https://pacyjst474.execute-api.us-east-1.amazonaws.com/dev
python test_analyse_device.py --stop-on-error
```

---

## Frontend

The React+Vite frontend (served from CloudFront + S3) provides:

- **Scenario selector** — 10 preset device scenarios matching the integration test suite
- **Device characteristics** — all input fields as two-column tables
- **Analysis pipeline** — calls `POST /analyse_device` with a 90s timeout
- **Results in three tabs:** ML Model · Policy Engine · LLM Engine
- **Summary banner** — final action (colour-coded), confidence score, expected match indicator

---

## Deployment

### One-command deploy (local)

```bash
# Deploy dev
bash scripts/deploy.sh dev

# Deploy prod
bash scripts/deploy.sh prod
```

The script runs: `sam build` → `sam deploy` → model artifact sync → `npm ci && npm run build` → `s3 sync` → CloudFront invalidation → smoke test.

### CI/CD (GitHub Actions)

| Branch | Trigger | Job |
|---|---|---|
| `develop` | push | `deploy-dev` |
| `main` | push | `deploy-prod` |
| any | PR to main | `lint-and-test` only |

Required GitHub secrets:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key |

Optional Actions variable: `BEDROCK_MODEL_ID` (defaults to `qwen.qwen3-30b-a3b`).

### Manual SAM deploy

```bash
sam build --use-container

sam deploy \
  --stack-name ewaste-optimizer-dev \
  --resolve-s3 \
  --resolve-image-repos \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    StageName=dev \
    BedrockModelId=qwen.qwen3-30b-a3b \
    BedrockRegion=us-east-1
```

---

## The 10 preset scenarios

| # | Name | Expected action | Notable characteristic |
|---|---|---|---|
| 1 | Brand-new healthy laptop | REDEPLOY | All signals minimal, score ≈ 0.027 |
| 2 | Young asset, minor wear | RESALE | Low wear, score ≈ 0.152 |
| 3 | Mid-life, average wear | REFURBISH | Moderate signals, score ≈ 0.505 |
| 4 | Overheating server, aging | REPAIR | Thermal + SMART breach, score ≈ 0.764 |
| 5 | End-of-life, all signals maxed | RECYCLE | All signals at maximum, score ≈ 0.960 |
| 6 | Borderline medium/high (~0.54) | REFURBISH | Right at 0.54 threshold |
| 7 | Borderline low/medium (~0.35) | RESALE | Right at 0.35 threshold |
| 8 | Old but well-maintained | RESALE | Age 60m but healthy hardware |
| 9 | Partial telemetry (completeness=0.45) | policy-only | ML skipped, policy engine only |
| 10 | High incidents, young device | REPAIR | Young but SMART + thermal breach |
