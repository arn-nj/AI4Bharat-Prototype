# API Integration — `src/api_integration/`

This folder contains the full runtime stack for the **E-Waste Asset Lifecycle Optimizer**: a FastAPI backend that runs the ML + Policy + LLM pipeline, a Streamlit demo frontend, and a PowerShell launcher that starts both with a single command.

---

## Folder structure

```
api_integration/
├── start.ps1          PowerShell launcher — starts backend and frontend together
├── backend/
│   ├── main.py                FastAPI application — routes, CORS, startup
│   ├── models.py              Pydantic request/response models
│   ├── device_analyser.py     Pipeline orchestrator — ML → Policy → LLM
│   └── test_analyse_device.py 10-scenario end-to-end test script
└── frontend/
    └── app.py                 Streamlit demo UI
```

---

## Prerequisites

Before starting the stack, make sure the following are in place.

### 1. Python virtual environment

Create and activate the project venv from the **repo root**:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Trained ML model

The backend requires a trained model artifact. Run the training script once:

```powershell
python src/model_training/train_model.py
```

This produces two files consumed at startup:

| File | Location |
|---|---|
| `risk_label_model.joblib` | `src/model_training/models/` |
| `model_metadata.json` | `src/model_training/models/` |

### 3. Environment variables (Azure OpenAI)

Copy the example env file and fill in your credentials:

```powershell
Copy-Item .env.example .env
```

Edit `.env` at the repo root:

```
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_API_VERSION=2024-02-01        # optional — this is the default
AZURE_CHAT_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_EMBEDDING_DEPLOYMENT_NAME=text-embedding-ada-002
```

> The `.env` file is gitignored. Never commit credentials to source control.

If the LLM credentials are missing or incorrect the pipeline will fall back to deterministic templates for the explanation and ITSM task — the rest of the pipeline (ML + policy) continues to work normally.

---

## Starting the stack

`start.ps1` starts both processes in separate terminal windows and prints a summary of all URLs.

```powershell
# From the repo root (or any directory)
.\src\api_integration\start.ps1
```

**Default URLs after startup:**

| Service | URL |
|---|---|
| FastAPI backend | http://localhost:8000 |
| Swagger UI (interactive API docs) | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Streamlit frontend | http://localhost:8501 |

### Optional parameters

| Parameter | Default | Description |
|---|---|---|
| `-Port <int>` | `8000` | Backend port |
| `-FrontendPort <int>` | `8501` | Streamlit port |
| `-NoReload` | off | Disables uvicorn `--reload` (use in production) |

```powershell
# Example — custom ports, no hot-reload
.\src\api_integration\start.ps1 -Port 9000 -FrontendPort 8502 -NoReload
```

To stop both services, close their respective terminal windows.

---

## Backend — `backend/`

The backend is a **FastAPI** application that exposes a single analysis endpoint. A shared `DeviceAnalyser` instance is created at startup, caching the ML model on first use.

### API routes

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe — returns `{"status": "ok"}` |
| `GET` | `/model_info` | ML model metadata (version, metrics, feature lists) |
| `POST` | `/analyse_device` | Full pipeline analysis — see below |

### `POST /analyse_device`

Accepts a `DeviceInput` JSON body and returns a complete `AnalysisResult`.

**Pipeline stages executed per request:**

| Stage | Module | Description |
|---|---|---|
| 1. Feature engineering | `device_analyser.py` | Derives `incident_rate_per_month`, `critical_incident_ratio`, `battery_degradation_rate`, `thermal_events_per_month` |
| 2. ML inference | `device_analyser.py` | Sklearn pipeline predicts `high` / `medium` / `low` risk label and class probabilities. Skipped when `data_completeness < 0.6`. |
| 3. Policy engine | `device_analyser.py` | Deterministic threshold rules map risk level to a lifecycle action: `RECYCLE` / `REPAIR` / `REFURBISH` / `RESALE` / `REDEPLOY` |
| 4. LLM engine | `src/llm_engine/llm.py` | Generates a ≤120-word explanation and a structured ITSM task JSON. Falls back to templates on timeout or missing credentials. |

**Policy rules (Stage 3):**

| Rule | Condition | Classification |
|---|---|---|
| `age_and_tickets` | `age ≥ 42 months AND total_incidents ≥ 5` | High |
| `thermal_threshold` | `thermal_events_count ≥ 10` | High |
| `smart_sectors_threshold` | `smart_sectors_reallocated ≥ 50` | High |
| *(partial)* | `age ≥ 30 AND tickets ≥ 3` OR `thermal ≥ 5` OR `smart ≥ 25` | Medium |
| *(none)* | No criteria met | Low |

**Action mapping:**

| Condition | Action |
|---|---|
| `risk_score ≥ 0.80` AND `age ≥ 42 months` | `RECYCLE` |
| `risk_score ≥ 0.70` AND device is repairable | `REPAIR` |
| `risk_score ≥ 0.50` | `REFURBISH` |
| `risk_score < 0.30` | `REDEPLOY` |
| else | `RESALE` |

*Repairable* = thermal breach OR SMART breach OR `overheating_issues == "True"`

### `DeviceInput` request fields

**Identity & context**

| Field | Type | Required | Description |
|---|---|---|---|
| `asset_id` | `str` | Yes | Unique asset identifier |
| `device_type` | `str` | Yes | `Laptop` \| `Server` \| `Desktop` |
| `brand` | `str` | Yes | Hardware manufacturer |
| `department` | `str` | Yes | Owning business unit |
| `region` | `str` | Yes | Geographic region |
| `usage_type` | `str` | default `Standard` | `Standard` \| `Heavy` \| `Light` |
| `os` | `str` | default `Windows 11` | Operating system |

**Age & manufacture**

| Field | Type | Required | Description |
|---|---|---|---|
| `age_in_months` | `int ≥ 0` | Yes | Asset age |
| `model_year` | `int ≥ 2000` | Yes | Manufacturing year |

**Hardware health**

| Field | Type | Required | Description |
|---|---|---|---|
| `battery_health_percent` | `float 0–100` | Yes | Current battery health |
| `battery_cycles` | `int ≥ 0` | Yes | Charge/discharge cycles |
| `smart_sectors_reallocated` | `int ≥ 0` | Yes | SMART drive health indicator |
| `thermal_events_count` | `int ≥ 0` | Yes | Overheating events in last 90 days |
| `overheating_issues` | `str` | default `False` | `"True"` \| `"False"` |
| `daily_usage_hours` | `float 0–24` | default `8.0` | Average daily usage |
| `performance_rating` | `int 1–5` | Yes | Subjective performance rating |

**Support tickets (90-day window)**

| Field | Type | Required | Description |
|---|---|---|---|
| `total_incidents` | `int ≥ 0` | Yes | Total tickets |
| `critical_incidents` | `int ≥ 0` | default `0` | P1/critical tickets |
| `high_incidents` | `int ≥ 0` | default `0` | High-severity tickets |
| `medium_incidents` | `int ≥ 0` | default `0` | Medium-severity tickets |
| `low_incidents` | `int ≥ 0` | default `0` | Low-severity tickets |
| `avg_resolution_time_hours` | `float ≥ 0` | default `24.0` | Average resolution time |

**Data quality**

| Field | Type | Required | Description |
|---|---|---|---|
| `data_completeness` | `float 0–1` | default `1.0` | Fraction of telemetry fields populated. Below `0.6` triggers the policy-only path. |

### `AnalysisResult` response fields

| Field | Type | Description |
|---|---|---|
| `asset_id` | `str` | Echoed from request |
| `final_action` | `str` | Lifecycle action from policy engine |
| `confidence_score` | `float` | Max ML class probability, or `0.5` on policy-only path |
| `ml_result` | `MLResult` | Risk label, score, confidence band, class probabilities |
| `policy_result` | `PolicyResult` | Classification, triggered rules, supporting signals |
| `llm_result` | `LLMResult` | Explanation text, ITSM task JSON, `llm_available` flag |

### End-to-end test script

`test_analyse_device.py` runs 10 hand-crafted scenarios against the live API and prints structured results for each, followed by a pass/fail summary table.

```powershell
# Backend must be running first
cd src/api_integration/backend
python test_analyse_device.py

# Optional flags
python test_analyse_device.py --url http://myserver:8000
python test_analyse_device.py --stop-on-error
```

---

## Frontend — `frontend/`

The frontend is a **Streamlit** demo UI that calls the backend's `POST /analyse_device` endpoint.

### Features

- **Scenario selector** — dropdown of the same 10 preset device scenarios used in `test_analyse_device.py`
- **Device characteristics** — all input fields displayed as two side-by-side tables (Identity & Usage / Hardware Health & Incidents)
- **Start Analysis button** — disabled with an info message when the backend is unreachable
- **Results in three labelled tabs:**
  - **ML Model** — risk label, risk score, confidence band, class probabilities, model version
  - **Policy Engine** — classification, recommended action, triggered rule IDs, supporting signals
  - **LLM Engine** — recommendation explanation, full ITSM task (title, priority, team, description, checklist)
- **Result banner** — final lifecycle action (colour-coded), confidence score, and match against expected action

### The 10 preset scenarios

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
| 9 | Partial telemetry (completeness=0.45) | policy-only | ML skipped, policy engine runs alone |
| 10 | High incidents, young device | REPAIR | Young but SMART + thermal breach |

---

## Logging

Both processes emit structured log lines to their respective terminal windows.

**Backend terminal (uvicorn):**

```
16:19:41 [INFO]  device_analyser — [TEST-001] Starting analysis pipeline ...
16:19:41 [INFO]  device_analyser — [TEST-001] ML result — label=low  score=0.027
16:19:41 [INFO]  device_analyser — [TEST-001] Policy result — action=REDEPLOY
16:19:41 [INFO]  device_analyser — [TEST-001] Calling LLM: generate_recommendation_explanation
16:19:42 [INFO]  device_analyser — [TEST-001] LLM explanation generated successfully
16:19:42 [INFO]  backend         — Request complete — asset_id=TEST-001  final_action=REDEPLOY  llm_available=True
```

**Frontend terminal (streamlit):**

```
16:19:40 [INFO]  frontend — Starting analysis for scenario '1. Brand-new healthy laptop' ...
16:19:40 [DEBUG] frontend — POST http://localhost:8000/analyse_device  asset_id=TEST-001
16:19:42 [INFO]  frontend — Analysis complete — final_action=REDEPLOY  confidence=0.932  llm_available=True
```

---

## File dependency map

```
start.ps1
  └── launches  backend/main.py      (uvicorn)
  └── launches  frontend/app.py      (streamlit)

backend/main.py
  └── imports   DeviceAnalyser       ← backend/device_analyser.py
  └── imports   DeviceInput,
                AnalysisResult       ← backend/models.py

backend/device_analyser.py
  └── imports   MLResult, PolicyResult,
                LLMResult, AnalysisResult  ← backend/models.py
  └── imports   LLMOpenAI                  ← src/llm_engine/llm.py
  └── loads     risk_label_model.joblib    ← src/model_training/models/
  └── loads     model_metadata.json        ← src/model_training/models/

frontend/app.py
  └── calls     POST /analyse_device       → backend/main.py (HTTP)
```
