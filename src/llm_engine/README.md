# LLM Engine — `src/llm_engine/`

This folder contains the language model layer of the E-Waste Asset Lifecycle Optimizer. It has two files:

| File | Role |
|---|---|
| `llm.py` | Amazon Bedrock client wrapper + four purpose-specific caller methods |
| `prompts.py` | Prompt builders for each GenAI use-case + fallback templates |

The LLM sits at **Stage 4** of the decision pipeline. It does **not** make lifecycle decisions — those are made by the ML model and policy engine. The LLM only converts already-made decisions into human-readable text, structured tasks, and answers.

---

## `llm.py` — The Client

### What it does

`LLMOpenAI` is the single entry point for all LLM calls. The class name is kept as `LLMOpenAI` for backward compatibility with existing imports in `device_analyser.py`. It handles:

- **Connection** — reads `AWS_REGION` and `BEDROCK_MODEL_ID` from the process environment (or a `.env` file at the repo root) and initialises a `boto3` `bedrock-runtime` client. When deployed on Lambda the IAM execution role provides credentials automatically; locally, set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.
- **Two generic transport methods** — `generic_llm()` uses the Bedrock Converse API (preferred), `generic_llm_rest()` uses the lower-level `InvokeModel` API. Both accept a `system_message` and a `question`/`query` string and return the model's response as a plain string.
- **Four purpose-specific methods** — each one calls the matching prompt builder from `prompts.py`, invokes `generic_llm()`, and handles errors gracefully. If the LLM takes longer than **10 seconds** or throws any exception, the method falls back to a deterministic template rather than failing the whole request.
- **Timeout enforcement** — a `_LLM_TIMEOUT_SECONDS = 10` constant governs the botocore read timeout. This matches the design requirement for graceful degradation when Bedrock is slow or unavailable.

### Configuration

| Variable | Default | Description |
|---|---|---|
| `AWS_REGION` | `us-east-1` | Bedrock service region |
| `BEDROCK_MODEL_ID` | `qwen.qwen3-30b-a3b` | Bedrock model identifier |
| `AWS_ACCESS_KEY_ID` | *(IAM role on Lambda)* | AWS access key — only needed locally |
| `AWS_SECRET_ACCESS_KEY` | *(IAM role on Lambda)* | AWS secret key — only needed locally |

> On Lambda the execution role (`AI4BhartLambdaExecutionRole`) automatically grants `bedrock:InvokeModel` and `bedrock:Converse` — no `.env` credentials are required.

### Purpose-specific methods at a glance

| Method | What it calls | Returns | Fallback |
|---|---|---|---|
| `generate_recommendation_explanation(...)` | `build_explanation_prompt` | `str` (≤120-word prose) | `fallback_explanation()` template string |
| `scaffold_itsm_task(...)` | `build_itsm_task_prompt` | `dict` (parsed JSON task) | `fallback_itsm_task()` minimal task dict |
| `process_compliance_document(...)` | `build_compliance_doc_prompt` | `dict` (parsed JSON analysis) | Dict with `INCOMPLETE` status |
| `answer_conversational_query(...)` | `build_conversational_prompt` | `str` (natural language answer) | Raises (no silent fallback needed) |

---

## `prompts.py` — The Prompt Builders

Each builder function returns a `(system_message, user_message)` tuple. The **system message** sets the LLM's role, rules, and output format constraints. The **user message** injects the specific asset data for that call.

Two additional **fallback helpers** (`fallback_explanation`, `fallback_itsm_task`) provide deterministic, template-based outputs when the LLM is unavailable — these are plain string/dict builders with no LLM call.

---

### Prompt 1 — Recommendation Explanation (`build_explanation_prompt`)

#### Why we need it

After the ML model and policy engine agree on a lifecycle action (RECYCLE, REPAIR, etc.), an IT manager needs to understand *why* in plain language before they can approve or reject it. A raw risk score like `0.82` and a label like `high` are not enough context for a human reviewer. This prompt turns the structured output of both engines into a factual, ≤120-word paragraph that the dashboard can display alongside the recommendation.

#### What the LLM is told to do

- Write **one paragraph**, no bullet points, no headings, max **120 words**.
- Reference **only** the data signals passed in — no invented facts.
- Use **hedged language** (`"signals suggest"`, `"may indicate"`) when `confidence_band` is LOW or MEDIUM; write assertively when it is HIGH.
- End with a one-sentence summary connecting the signals to the recommended action.
- The system message explicitly states: *"You do NOT make decisions. You only explain decisions already made by the system."*

#### Input data required

| Parameter | Type | Where it comes from |
|---|---|---|
| `asset_id` | `str` | Asset record |
| `device_type` | `str` | Asset record (`Laptop`, `Server`, `Desktop`) |
| `age_months` | `int` | Derived from `purchase_date` |
| `department` | `str` | Asset record |
| `region` | `str` | Asset record |
| `risk_score` | `float` | Risk score formula output (0.0–1.0) |
| `risk_label` | `str` | ML classifier output (`high` / `medium` / `low`) |
| `confidence_band` | `str` | Derived from `max_proba`: `HIGH` ≥0.90, `MEDIUM` 0.70–0.89, `LOW` <0.70 |
| `recommended_action` | `str` | Policy/recommendation engine output (`RECYCLE` / `REPAIR` / `REFURBISH` / `RESALE` / `REDEPLOY`) |
| `supporting_signals` | `list[str]` | Human-readable list of triggered thresholds, e.g. `"Age: 48 months (exceeds 42-month threshold)"` |
| `policy_result` | `dict` | `{"classification": "High", "triggered_rules": ["age_and_tickets"]}` |
| `ml_result` *(optional)* | `dict` | `{"risk_score": 0.85, "confidence_interval": [0.78, 0.92]}` — omit if telemetry completeness was below threshold |
| `telemetry` *(optional)* | `dict` | `{"battery_cycles": int, "smart_sectors_reallocated": int, "thermal_events_count": int}` |
| `tickets` *(optional)* | `dict` | `{"total_incidents": int, "critical_incidents": int, "avg_resolution_time_hours": float}` |

#### Output

A single string of plain prose, ≤120 words.

---

### Prompt 2 — ITSM Task Scaffolding (`build_itsm_task_prompt`)

#### Why we need it

Once a human approves a recommendation, an ITSM ticket must be raised so the operations team knows exactly what to do and in what order. Writing these tickets manually for every asset is time-consuming and inconsistent. This prompt generates a fully structured, ready-to-post ITSM task — with a title, description, step-by-step checklist, priority, and assigned team — tailored to the specific asset and region.

#### What the LLM is told to do

- Respond with **only a valid JSON object** — no prose, no markdown fences.
- JSON must have exactly five fields: `title`, `description`, `checklist`, `priority`, `assigned_team`.
- The checklist must **always** include: (a) verifying user data backup, (b) updating the CMDB on completion, and (c) any region-specific compliance steps passed in.
- `priority` must be one of `"High"` / `"Medium"` / `"Low"`.

#### Input data required

| Parameter | Type | Where it comes from |
|---|---|---|
| `asset_id` | `str` | Asset record |
| `recommended_action` | `str` | Recommendation engine output |
| `rationale` | `str` | Recommendation engine rationale text |
| `confidence_score` | `float` | Recommendation engine confidence (0.0–1.0) |
| `device_type` | `str` | Asset record |
| `department` | `str` | Asset record |
| `region` | `str` | Asset record |
| `age_months` | `int` | Derived from `purchase_date` |
| `compliance_requirements` *(optional)* | `list[str]` | Region-specific requirements, e.g. `["E-waste certificate required (India)", "Chain of custody documentation"]` |

#### Output

A Python `dict` parsed from the LLM's JSON response, with the structure:

```json
{
  "title": "Recycle Asset LAP-2891 — High Risk Laptop (India Region)",
  "description": "...",
  "checklist": ["Verify user data backup completed", "..."],
  "priority": "High",
  "assigned_team": "Asset Disposition — India"
}
```

---

### Prompt 3 — Compliance Document Processing (`build_compliance_doc_prompt`)

#### Why we need it

Before an irreversible disposal action (especially RECYCLE) can proceed, region-specific compliance documents must be uploaded and verified — for example, an e-waste certificate, chain of custody, and disposal invoice are all required in India. These documents arrive as PDFs whose text is extracted and passed to the LLM for structured analysis. Manual review of every document is impractical at scale. This prompt extracts the required fields, flags anything missing, and returns a machine-readable verification status that the compliance service can act on automatically.

#### What the LLM is told to do

- Respond with **only a valid JSON object**.
- JSON must have exactly five fields: `summary`, `extracted_entities`, `missing_fields`, `verification_status`, `recommendations`.
- `verification_status` rules: `"VERIFIED"` if all required fields are found, `"INCOMPLETE"` if some are missing, `"REJECTED"` if the document type doesn't match or content is unreadable.
- If a field is present but illegible, add it to **both** `extracted_entities` (as `"UNCLEAR"`) and `missing_fields`.
- **Never invent data** — only extract what is present in the document text.

#### Input data required

| Parameter | Type | Where it comes from |
|---|---|---|
| `document_type` | `str` | Upload metadata (`certificate`, `invoice`, `chain_of_custody`) |
| `region` | `str` | Asset record |
| `asset_id` | `str` | Asset record |
| `file_content` | `str` | Text extracted from the uploaded PDF/document |
| `required_fields` | `list[str]` | Configured per document type, e.g. `["certification_number", "vendor_name", "disposal_date", "weight_in_kg", "destruction_method"]` |
| `region_requirements` *(optional)* | `dict` | e.g. `{"India": ["e_waste_certificate", "chain_of_custody", "disposal_invoice"]}` |

#### Output

A Python `dict` parsed from the LLM's JSON response:

```json
{
  "summary": "E-waste certificate for LAP-2891 issued by GreenCycle India on 2026-02-10...",
  "extracted_entities": {
    "certification_number": "GC-2026-00412",
    "vendor_name": "GreenCycle India Pvt Ltd",
    "disposal_date": "2026-02-10",
    "weight_in_kg": "2.4",
    "destruction_method": "UNCLEAR"
  },
  "missing_fields": ["destruction_method"],
  "verification_status": "INCOMPLETE",
  "recommendations": ["Obtain updated certificate with destruction method clearly stated."]
}
```

---

### Prompt 4 — Conversational Insights (`build_conversational_prompt`)

#### Why we need it

IT managers and asset teams need to ask ad-hoc questions about the state of the asset fleet — for example: *"How many laptops in India are pending recycling?"* or *"What is the average risk score for the Engineering department?"* — without writing SQL or navigating dashboards. This prompt lets users query the structured semantic layer in plain English and receive a grounded, cited answer with suggested follow-ups.

#### What the LLM is told to do

- Answer **directly and concisely** (main answer ≤150 words).
- Always **cite** which table(s) and field(s) from the semantic layer were used.
- If the data is insufficient, say so clearly and state what would be needed.
- End every response with a section labelled `"Suggested follow-up queries:"` containing exactly 2–3 follow-up questions.
- **Never make up numbers** — only use values from the `context_data` provided.
- When `context_data` is absent, describe what data would need to be retrieved and how.

#### Input data required

| Parameter | Type | Where it comes from |
|---|---|---|
| `user_query` | `str` | User's natural-language question from the dashboard |
| `semantic_layer_schema` *(optional)* | `dict` | Table/field map of the data layer — defaults to the schema defined in `design.md` (assets, recommendations, risk_assessments, approval_audits) |
| `available_aggregations` *(optional)* | `list[str]` | Supported aggregations (e.g. `count_by_state`, `avg_risk_score`) — defaults to the list in `prompts.py` |
| `context_data` *(optional)* | `dict` | Pre-fetched query results to answer from directly; if omitted, the LLM produces a query plan instead |

#### Output

A plain string containing the answer, data provenance, and suggested follow-up queries.

---

## Fallback Templates

When the LLM is unavailable or exceeds the 10-second timeout, the two fallback helpers in `prompts.py` are used instead of raising an exception:

| Helper | Used by | Returns |
|---|---|---|
| `fallback_explanation(...)` | `generate_recommendation_explanation()` | A short, template-filled sentence covering action, risk score, age, and incident count |
| `fallback_itsm_task(...)` | `scaffold_itsm_task()` | A minimal task dict with a generic checklist, derived priority, and region-routed team name |

These ensure the system always produces a usable output even when the LLM service is down, consistent with the graceful degradation principle in `design.md`.

---

## Environment Variables

When deployed on Lambda, no `.env` credentials are needed — the IAM execution role provides access to Bedrock automatically. For local development, set the following in a `.env` file at the project root or as shell exports:

```
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=qwen.qwen3-30b-a3b
AWS_ACCESS_KEY_ID=<your-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-secret-access-key>
```

> `AWS_REGION` and `BEDROCK_MODEL_ID` have sensible defaults and can be omitted if you are using the standard model in `us-east-1`. Only the key pair is strictly required for local dev; on Lambda, omit both key variables.
