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
├── backend/
│   ├── db/                 SQLAlchemy ORM — AssetRow, RiskAssessmentRow, RecommendationRow, AuditRow
│   ├── orm_models/         Pydantic schemas — asset, risk, recommendation, audit
│   ├── services/           Business logic — risk_engine, recommendation, approval, kpi, llm, data_generator
│   ├── routers/            FastAPI routers — assets, assess, approvals, kpis, ai, demo, audit_trail
│   └── main.py             App entry-point + Mangum Lambda handler (19 routes)
├── frontend/               React 18 + Vite 5 + Tailwind + recharts — 7-page SPA
│   └── src/pages/          Dashboard, AssessDevice, AssetInventory, ApprovalQueue,
│                           AuditTrail, AIAssistant, Settings
├── llm_engine/             Amazon Bedrock client (Qwen3-30B) + structured prompt builders
├── model_training/         Training data (1235 records), Jupyter notebooks, sklearn Pipeline
│   └── models/             risk_label_model.joblib (AUC-ROC 0.9962)
└── storage/                S3 helper for model artifacts

scripts/
├── deploy.sh               Full-stack deploy (sam build → SAM deploy → npm build → S3 sync)
├── start.ps1               Windows local dev launcher (FastAPI + Vite dev server)
└── start.sh                Linux/WSL local dev launcher
```

**Data flow:**

```
POST /api/assess/{asset_id}
  → risk_engine  (policy rules 60% + sklearn ML 40%)
  → recommendation (action mapping + Bedrock LLM rationale + ITSM task)
  → DB: RiskAssessmentRow + RecommendationRow, asset.state = review_pending

POST /api/approvals/{id}/decide
  → approval (state machine) → AuditRow (immutable audit trail)

GET /api/kpis
  → kpi service (fleet metrics + CO2/landfill/trees environmental impact)
```

**AWS stack:**

```
Browser → CloudFront → S3 (React build)
Browser → API Gateway → Lambda (FastAPI/Mangum) → Amazon Bedrock (Qwen3-30B)
                                                 → S3 (model artifacts)
                                                 → /tmp/ewaste.db (SQLite, per-invocation)
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
BEDROCK_MODEL_ID=qwen.qwen3-next-80b-a3b

# S3 bucket for model artifacts (optional — falls back to local files)
S3_BUCKET_NAME=ewaste-asset-optimizer-dev-992332682921

# Database
# Production (RDS PostgreSQL):
# DATABASE_URL=postgresql+psycopg2://user:pass@your-rds-host.region.rds.amazonaws.com:5432/ewaste
# Local dev (SQLite — omit this line, SQLite is the automatic fallback):
# DATABASE_URL=sqlite:///./ewaste.db
```

> **Database**: Production deployments use **Amazon RDS (PostgreSQL)**. The `DATABASE_URL` env var is passed to Lambda via the SAM `RDSConnectionString` parameter at deploy time. Locally, omitting `DATABASE_URL` falls back to SQLite automatically.

> If Bedrock credentials are missing the pipeline falls back to deterministic templates — ML + Policy stages continue to work normally.

### 4 — Start the full local stack

```powershell
# Windows — opens two terminal windows
.\scripts\start.ps1

# Custom ports
.\scripts\start.ps1 -Port 9000 -FrontendPort 5174
```

```bash
# Linux / WSL
./scripts/start.sh
```

| Service | Default URL |
|---|---|
| FastAPI backend | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| React frontend (Vite) | http://localhost:5173 |

**Or start manually (always run from repo root):**

```bash
# Backend — MUST be run from repo root (not from src/backend/)
.venv/bin/uvicorn src.backend.main:app --reload --port 8000

# Frontend (separate terminal)
cd src/frontend && npm run dev
```

---

## API reference

All endpoints are prefixed with `/api`. Swagger UI: `http://localhost:8000/docs`

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Service health + version |
| `GET` | `/api/model_info` | ML model metadata (AUC-ROC, features, version) |
| `POST` | `/api/assets` | Register a new IT asset |
| `GET` | `/api/assets` | List assets (filters: department, region, state, search) |
| `GET` | `/api/assets/{asset_id}` | Get a single asset |
| `DELETE` | `/api/assets/{asset_id}` | Delete an asset |
| `POST` | `/api/assess/{asset_id}` | Run full risk + recommendation pipeline |
| `GET` | `/api/approvals/queue` | List assets pending approval (`review_pending`) |
| `POST` | `/api/approvals/{id}/decide` | Approve or reject a recommendation |
| `GET` | `/api/kpis` | Fleet KPIs + environmental impact metrics |
| `GET` | `/api/audit` | Audit trail (filters: asset_id, actor) |
| `POST` | `/api/ai/chat` | LLM conversational assistant |
| `POST` | `/api/ai/suggest-policy` | AI-generated policy threshold suggestions |
| `POST` | `/api/demo/generate` | Generate synthetic fleet data (`count`, `auto_assess`) |
| `DELETE` | `/api/demo/reset` | Wipe all data (dev/demo use) |

### Assessment pipeline (`POST /api/assess/{asset_id}`)

| # | Stage | Description |
|---|---|---|
| 1 | Policy engine | Deterministic threshold rules (age ≥ 42 months, tickets ≥ 5, thermal ≥ 10, SMART ≥ 50) |
| 2 | ML inference | sklearn Pipeline (Gradient Boosting) — high/medium/low + class probabilities |
| 3 | Score blend | Policy (60%) + ML (40%) when ML confidence ≥ 0.80 |
| 4 | Action mapping | risk score → Redeploy / Resale / Refurbish / Recycle |
| 5 | LLM rationale | Bedrock Qwen3-30B generates explanation + ITSM task JSON |

### KPI response includes environmental impact

| Field | Description |
|---|---|
| `co2_saved_kg` | Estimated CO₂ savings vs. new device procurement |
| `landfill_reduction_kg` | Estimated e-waste diverted from landfill |
| `carbon_offset_trees` | Equivalent CO₂ absorbed by trees |
| `material_recovery_pct` | Percentage of devices sent to recycle/refurbish |

---

## Frontend

The React 18 + Vite 5 + Tailwind SPA provides 7 pages:

| Page | Path | Description |
|---|---|---|
| Dashboard | `/` | KPI strip, action distribution donut, risk bars, environmental impact |
| Assess Device | `/assess` | Asset form → full pipeline result with ML probabilities + ITSM task |
| Asset Inventory | `/assets` | Paginated table with department/state filters |
| Approval Queue | `/approvals` | Split-view: pending queue cards + approve/reject decision panel |
| Audit Trail | `/audit` | Full immutable audit log |
| AI Assistant | `/ai` | Conversational LLM chat with policy Q&A |
| Settings | `/settings` | Demo generator + policy threshold editor + AI policy suggestions |


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

Optional Actions variable: `BEDROCK_MODEL_ID` (defaults to `qwen.qwen3-next-80b-a3b`).

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
    BedrockModelId=qwen.qwen3-next-80b-a3b \
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
