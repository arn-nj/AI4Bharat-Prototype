# Hackathon Submission Form: Intelligent E-Waste & Asset Lifecycle Optimizer

## 1. Proposed Architecture Stack [Multiple Select]

**Selected Components:**
- ✅ **a. Amazon Bedrock**
- ✅ **b. AWS Lambda**
- ✅ **c. Amazon S3**
- ✅ **d. Amazon DynamoDB**
- ⬜ e. Amazon SageMaker
- ✅ **f. Other: Amazon API Gateway, AWS Step Functions, Amazon CloudWatch, Amazon EventBridge**

### Reasoning:

**Amazon Bedrock** - Essential for the GenAI Service component that provides:
- Recommendation explanations (≤120 words, factual, hedged language)
- ITSM task scaffolding (titles, descriptions, checklists)
- Compliance document summarization
- Conversational insights over structured data

**AWS Lambda** - Ideal serverless compute for:
- Data Ingestion Service (CSV parsing and validation)
- Risk Assessment Engine (policy rules and ML model invocation)
- Recommendation Service (lifecycle action generation)
- ITSM Connector (REST API integration with retry logic)
- Compliance Service (document validation)
- Event-driven architecture with exponential backoff retry patterns

**Amazon S3** - Required for:
- CSV file upload and storage for asset data ingestion
- Compliance document storage (certificates, invoices, chain of custody)
- ML model artifact storage
- Audit log archival (immutable snapshots)
- Static web hosting for Dashboard UI

**Amazon DynamoDB** - Optimal NoSQL database for:
- Asset records with high-velocity state changes (10 states in state machine)
- Telemetry data with sparse/variable schema
- TicketsAggregate time-series data
- RiskAssessment records with versioning
- ApprovalAudit immutable records (single-table design pattern)
- Fast key-value lookups for asset_id-based queries
- Built-in TTL for recommendation expiration

**Amazon SageMaker** - Not selected because:
- ML model requirements are modest (logistic regression/gradient boosting with AUC-ROC ≥0.70)
- Models can be packaged and invoked via Lambda without full SageMaker infrastructure
- Budget and complexity considerations favor simpler deployment
- Could be added later if model complexity increases

**Other AWS Services:**
- **Amazon API Gateway** - REST API for Dashboard and external integrations
- **AWS Step Functions** - Orchestrates approval workflow and state machine transitions
- **Amazon CloudWatch** - Logging, monitoring, and KPI metric tracking
- **Amazon EventBridge** - Event-driven architecture for async processing and ITSM integration

---

## 2. GenAI Model Used: What models do you plan to invoke via Bedrock?

**Primary Model: Claude 3.5 Sonnet**

### Reasoning:

**Use Cases Mapped to Model Capabilities:**

1. **Recommendation Explanations** (Requirement 8)
   - Need: Factual summaries ≤120 words with hedged language
   - Why Claude: Excellent instruction following, concise reasoning, natural uncertainty expression
   - Prompt strategy: JSON schema validation with word count constraints

2. **ITSM Task Scaffolding** (Requirement 9)
   - Need: Generate titles, descriptions, and actionable checklists
   - Why Claude: Strong structured output generation, understands technical workflows
   - Output format: JSON with title, description, checklist arrays

3. **Compliance Document Processing** (Requirement 10)
   - Need: Extract key compliance points from certificates and legal documents
   - Why Claude: Superior document understanding, handles technical/legal language
   - Processing: Extract entities, dates, requirements, verification status

4. **Conversational Insights** (Requirement 11)
   - Need: Natural language queries over structured data (semantic layer)
   - Why Claude: Advanced reasoning for query understanding and data interpretation
   - Integration: Text-to-SQL capabilities with provenance tracking

**Model Configuration:**
- Temperature: 0.3 (balanced between determinism and natural language)
- Max tokens: 500 (aligned with explanation length requirements)
- Timeout: 10 seconds (with graceful fallback to templates)
- JSON mode enabled for structured outputs

**Fallback Strategy:**
- Primary: Claude 3.5 Sonnet via Bedrock
- Fallback: Template-based explanations using policy rules
- Graceful degradation ensures system continues without GenAI dependency

**Why Not Other Models:**
- **Claude 3 Haiku**: Considered for cost optimization but explanations require nuanced reasoning
- **Titan models**: Less sophisticated for technical document processing
- **Jurassic models**: Claude provides better instruction adherence for our structured output needs
- **Multi-model approach**: Avoided for simplicity during hackathon timeframe

---

## 3. Data Strategy: What are our data sources and how will you store and process the data on AWS?

### Data Sources

**Primary Sources:**
1. **CSV Files** - Asset metadata (purchase date, department, region, device type)
2. **API Endpoints** - Telemetry data (battery cycles, SMART sectors, thermal events)
3. **ITSM System API** - Ticket aggregates (incidents, severity, resolution times)
4. **User Uploads** - Compliance documents (certificates, invoices, chain of custody)

### Storage Architecture

**Amazon S3 (Object Storage):**
```
s3://ewaste-optimizer-{account-id}/
├── raw-data/
│   ├── csv-uploads/{date}/{filename}.csv
│   └── compliance-docs/{asset-id}/{document-id}.pdf
├── processed-data/
│   ├── normalized-assets/{date}/
│   └── aggregated-tickets/{date}/
├── ml-models/
│   ├── risk-classifier-v{version}.pkl
│   └── model-metadata.json
└── audit-archive/
    └── snapshots/{year}/{month}/{audit-id}.json
```

**Amazon DynamoDB (Transactional Data):**

*Single-Table Design Pattern:*

| PK | SK | EntityType | Attributes |
|---|---|---|---|
| ASSET#{asset-id} | METADATA | Asset | purchase_date, department, region, state, data_completeness |
| ASSET#{asset-id} | TELEMETRY#{timestamp} | Telemetry | battery_cycles, smart_sectors, thermal_events |
| ASSET#{asset-id} | TICKETS#{window-start} | TicketsAggregate | total_incidents, critical_count, resolution_time |
| ASSET#{asset-id} | RISK#{timestamp} | RiskAssessment | risk_score, confidence_band, model_version |
| ASSET#{asset-id} | RECOMMENDATION#{rec-id} | Recommendation | action, confidence, rationale, explanation |
| ASSET#{asset-id} | AUDIT#{timestamp} | ApprovalAudit | actor, decision, asset_snapshot, rec_snapshot |
| ASSET#{asset-id} | COMPLIANCE#{doc-id} | ComplianceDocument | document_type, region, verification_status |
| REGION#{region} | CONFIG#{version} | RegionConfig | compliance_requirements, required_documents |

**GSI-1:** `EntityType-CreatedAt-index` for querying by entity type
**GSI-2:** `State-Region-index` for dashboard filtering

**TTL Field:** `expires_at` on Recommendation entities (auto-cleanup)

### Data Processing Pipeline

**Ingestion Flow:**
```
CSV Upload → S3 Event → Lambda (Validation) → DynamoDB → EventBridge → Risk Assessment Lambda
```

**Processing Stages:**

1. **Data Ingestion Service** (Lambda)
   - Trigger: S3 PUT event
   - Process: Parse CSV, validate schema, calculate data_completeness
   - Output: Write to DynamoDB, publish to EventBridge

2. **Risk Assessment Engine** (Lambda)
   - Trigger: EventBridge (AssetIngested event)
   - Process: Apply policy rules, invoke ML model (if telemetry sufficient)
   - Output: Write RiskAssessment to DynamoDB

3. **Recommendation Service** (Lambda + Bedrock)
   - Trigger: EventBridge (RiskAssessed event)
   - Process: Generate recommendation, call Bedrock for explanation
   - Output: Write Recommendation to DynamoDB, transition state to ReviewPending

4. **Approval Workflow** (Step Functions)
   - Trigger: Manual approval via API Gateway
   - Process: State machine orchestration, create immutable snapshot
   - Output: Write ApprovalAudit to DynamoDB, transition to ApprovedFor{Action}

5. **ITSM Integration** (Lambda + EventBridge)
   - Trigger: State transition to ApprovedFor{Action}
   - Process: Call ITSM API with retry logic, scaffold task via Bedrock
   - Output: Create ITSM task, transition to WorkflowInProgress

**Data Quality and Completeness:**
- Calculate `data_completeness` = (available_fields / total_fields)
- Mark assets with completeness < 0.6 for policy-only evaluation
- Store data quality metadata alongside asset records

**Compliance Data Management:**
- Store documents in S3 with signed URLs (30-minute expiry)
- Reference S3 URIs in DynamoDB ComplianceDocument records
- Process via Bedrock for summarization and validation
- Block disposal actions until `verification_status = VERIFIED`

**Audit Trail and Immutability:**
- DynamoDB records are append-only (no updates to audit entities)
- Archive snapshots to S3 Glacier for long-term retention
- Maintain `asset_snapshot` and `recommendation_snapshot` in JSON

**KPI Aggregation:**
- CloudWatch Metrics for real-time KPIs (GenAI health, prediction coverage)
- DynamoDB Streams → Lambda → Aggregate calculations
- Tag metrics with `ProvenanceTag` (observed_outcome, policy_default, model_estimate)

---

## 4. 24-Hour Goal: What's the first technical milestone you will achieve once credits are credited to your account?

### Milestone: End-to-End "Happy Path" Demo Pipeline

**Goal:** Demonstrate a complete asset lifecycle from CSV ingestion through risk assessment to human-readable recommendation with GenAI explanation.

### Deliverables (24 Hours):

**1. Infrastructure Setup (Hours 0-4)**
- Deploy AWS CDK stack with:
  - S3 bucket for CSV uploads
  - DynamoDB table with single-table design
  - Lambda functions for ingestion and risk assessment
  - API Gateway for file upload endpoint
  - Bedrock access configuration (Claude 3.5 Sonnet)
- Set up CloudWatch logging and basic monitoring

**2. Core Data Pipeline (Hours 4-12)**
- **Data Ingestion Service** Lambda:
  - Parse CSV with pandas
  - Validate asset schema (purchase_date, department, region, device_type)
  - Calculate data_completeness score
  - Write to DynamoDB
  - Publish AssetIngested event to EventBridge
- **Sample Data:** Create synthetic CSV with 50 assets (mix of high/medium/low risk profiles)

**3. Risk Assessment Engine (Hours 12-18)**
- **Policy Engine** implementation:
  - Apply rule: High risk if `age >= 42 months AND tickets >= 5`
  - Apply rule: High risk if `thermal_events >= 10 OR smart_sectors >= 50`
  - Assign confidence bands (Low/Medium/High)
- **Mock ML Model:** Return random risk scores with confidence intervals
- Write RiskAssessment records to DynamoDB

**4. Recommendation + GenAI Integration (Hours 18-24)**
- **Recommendation Service** Lambda:
  - Map risk scores to lifecycle actions (redeploy, repair, refurbish, resale, recycle)
  - Call Bedrock (Claude) with structured prompt:
    ```
    Generate a factual explanation (≤120 words) for this recommendation:
    Asset: {asset_id}, Age: {age} months, Risk: {risk_score}
    Action: {recommended_action}
    Supporting signals: {signals}
    Use hedged language for uncertainties.
    ```
  - Validate JSON schema output
  - Implement 10-second timeout with template fallback
- Write Recommendation with GenAI explanation to DynamoDB

**5. Demo Web Interface (Hours 22-24)**
- Simple HTML/JavaScript dashboard hosted on S3:
  - File upload form (CSV)
  - Display ingested assets in table
  - Show recommendations with GenAI explanations
  - Highlight confidence bands with color coding

### Success Criteria:

✅ Upload 50-asset CSV → See all assets parsed in DynamoDB  
✅ Trigger risk assessment → See RiskAssessment records with policy classification  
✅ Generate recommendations → See Recommendation records with Claude-generated explanations  
✅ Dashboard displays → Visual confirmation of end-to-end pipeline  
✅ CloudWatch logs → Trace request flow through all Lambda functions  

### Demo Script:

1. **Upload CSV:** `sample_assets.csv` with 50 laptops (various ages, ticket counts, telemetry)
2. **Wait 30 seconds:** For async processing
3. **Open Dashboard:** Show asset table with completeness scores
4. **Filter by risk:** Display high-risk assets with recommendations
5. **Read explanation:** Show GenAI-generated rationale for "Recycle" recommendation
6. **Show logs:** Demonstrate CloudWatch tracing and error handling

### What We'll Defer (Post-24 Hours):

- Approval workflow and state machine
- ITSM integration with retry logic
- Compliance document processing
- ML model training (use policy-only for demo)
- Full authentication and authorization
- Production-grade error handling and monitoring

### Why This Milestone?

**Demonstrates Core Value:**
- Proves GenAI integration with Bedrock works
- Shows data ingestion → analysis → recommendation pipeline
- Validates single-table DynamoDB design
- Provides tangible demo for stakeholders

**De-Risks Technical Challenges:**
- Bedrock API integration and prompt engineering
- Lambda cold start performance
- DynamoDB access patterns
- S3 event triggering

**Foundation for Iteration:**
- Remaining features build on this pipeline
- Can incrementally add approval workflow, ITSM, compliance
- Architecture proven before adding complexity

**Hackathon-Friendly:**
- Achievable in 24 hours with focused effort
- Produces working demo (not just slides)
- Clear stopping point with tangible output
