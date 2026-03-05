// API service layer — all calls to the FastAPI backend
// VITE_API_URL is injected at build time (e.g. https://pacyjst474.execute-api.us-east-1.amazonaws.com/dev)
// In local dev it is empty, so requests fall through to the Vite proxy.
const BASE = (import.meta.env.VITE_API_URL ?? '') + '/api';

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // FastAPI 422: detail is an array of validation errors
    const detail = body?.detail;
    const msg = Array.isArray(detail)
      ? detail.map((e: { loc?: string[]; msg?: string }) => `${e.loc?.slice(1).join('.')}: ${e.msg}`).join('; ')
      : (typeof detail === 'string' ? detail : `HTTP ${res.status}`);
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

// ── Assets ────────────────────────────────────────────────────

export const getAssets = (params?: Record<string, string>) => {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  return apiFetch<AssetOut[]>(`/assets${qs}`);
};

export const getAsset = (assetId: string) =>
  apiFetch<AssetOut>(`/assets/${assetId}`);

export const createAsset = (payload: AssetCreate) =>
  apiFetch<AssetOut>('/assets', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const deleteAsset = (assetId: string) =>
  apiFetch<void>(`/assets/${assetId}`, { method: 'DELETE' });

// ── Assessment ────────────────────────────────────────────────

export const assessAsset = (assetId: string) =>
  apiFetch<AssessmentResultOut>(`/assess/${assetId}`, { method: 'POST' });

// ── Approvals ─────────────────────────────────────────────────

export const getApprovalQueue = () =>
  apiFetch<ApprovalQueueItem[]>('/approvals/queue');

export const decideApproval = (recommendationId: string, payload: ApprovalRequest) =>
  apiFetch<AuditEntry>(`/approvals/${recommendationId}/decide`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });

// ── KPIs ──────────────────────────────────────────────────────

export const getKPIs = () => apiFetch<KPIOut>('/kpis');

// ── AI ────────────────────────────────────────────────────────

export const chat = (query: string) =>
  apiFetch<{ response: string }>('/ai/chat', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });

export const suggestPolicy = (settings: PolicySettings) =>
  apiFetch<{ suggestion: string }>('/ai/suggest-policy', {
    method: 'POST',
    body: JSON.stringify(settings),
  });

export const getFleetNarrative = () =>
  apiFetch<{ narrative: string }>('/ai/fleet-narrative');

export const getLLMOpinion = (assetId: string) =>
  apiFetch<LLMPrediction>(`/ai/predict/${assetId}`);

export const approveAll = (payload: { rationale: string; actor: string }) =>
  apiFetch<{ approved: number; failed: number; message: string }>('/approvals/approve-all', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export interface ComplianceDocRequest {
  document_type: string;
  region: string;
  asset_id: string;
  file_content: string;
}

export interface ComplianceDocResult {
  summary: string;
  extracted_entities: Record<string, string>;
  missing_fields: string[];
  verification_status: 'VERIFIED' | 'INCOMPLETE' | 'REJECTED';
  recommendations: string[];
}

export const analyzeComplianceDoc = (payload: ComplianceDocRequest) =>
  apiFetch<ComplianceDocResult>('/ai/analyze-doc', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

// ── Demo ──────────────────────────────────────────────────────

export const generateDemo = (payload: GenerateRequest) =>
  apiFetch<GenerateResult>('/demo/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const resetDemo = () =>
  apiFetch<{ message: string }>('/demo/reset', { method: 'DELETE' });

// ── Audit ─────────────────────────────────────────────────────

export const getAuditTrail = (params?: Record<string, string>) => {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  return apiFetch<AuditEntryRow[]>(`/audit${qs}`);
};

// ── Model Info ────────────────────────────────────────────────

export const getModelInfo = () => apiFetch<ModelInfo>('/model_info');

// ── Types (co-located for convenience) ───────────────────────

export interface AssetCreate {
  device_type: string;
  brand?: string;
  model_name?: string;
  model_year?: number;
  os?: string;
  purchase_date?: string;
  department: string;
  region: string;
  usage_type?: string;
  daily_usage_hours?: number;
  performance_rating?: number;
  battery_health_pct?: number;
  overheating_issues?: boolean;
  battery_cycles?: number;
  smart_sectors_reallocated?: number;
  thermal_events_count?: number;
  total_incidents?: number;
  critical_incidents?: number;
  high_incidents?: number;
  medium_incidents?: number;
  low_incidents?: number;
  avg_resolution_time_hours?: number;
}

export interface AssetOut extends AssetCreate {
  asset_id: string;
  age_months: number;
  data_completeness: number;
  current_state: string;
  created_at?: string;
  updated_at?: string;
}

export interface MLScores {
  ml_risk_label: string;
  p_high: number;
  p_medium: number;
  p_low: number;
  model_version: string;
}

export interface TriggeredRule {
  rule: string;
  description: string;
  met: boolean;
}

export interface RiskAssessmentOut {
  asset_id: string;
  risk_level: 'high' | 'medium' | 'low';
  risk_score: number;
  confidence_band: 'HIGH' | 'MEDIUM' | 'LOW';
  eval_mode: string;
  triggered_rules: TriggeredRule[];
  ml_scores?: MLScores;
  policy_version: string;
  assessed_at: string;
}

export interface RecommendationOut {
  recommendation_id: string;
  asset_id: string;
  action: 'recycle' | 'repair' | 'refurbish' | 'redeploy' | 'resale';
  confidence_score: number;
  rationale: string;
  supporting_signals: string[];
  itsm_task?: Record<string, unknown>;
  policy_version: string;
  model_version: string;
  created_at: string;
}

export interface AssessmentResultOut {
  asset_id: string;
  risk: RiskAssessmentOut;
  recommendation: RecommendationOut;
  llm_prediction?: LLMPrediction | null;
}

export interface LLMPrediction {
  risk_level: string;
  action: string;
  reasoning: string;
  agrees_with_ml?: boolean | null;
}

export interface ApprovalQueueItem {
  recommendation_id: string;
  asset_id: string;
  device_type: string;
  brand?: string;
  department: string;
  region: string;
  age_months: number;
  action: string;
  confidence_score: number;
  rationale: string;
  policy_version: string;
  model_version: string;
  created_at: string;
  risk_level?: string | null;
  risk_score?: number | null;
  confidence_band?: string | null;
}

export interface ApprovalRequest {
  decision: 'approved' | 'rejected';
  rationale: string;
  actor: string;
}

export interface AuditEntry {
  audit_id: string;
  recommendation_id: string;
  asset_id: string;
  action: string;
  decision: string;
  rationale: string;
  actor: string;
  previous_state: string;
  new_state: string;
  asset_snapshot: Record<string, unknown>;
  recommendation_snapshot: Record<string, unknown>;
  timestamp: string;
  llm_impact?: string | null;
}

export interface AuditEntryRow {
  audit_id: string;
  recommendation_id: string;
  asset_id: string;
  action: string;
  decision: string;
  rationale: string;
  actor: string;
  previous_state: string;
  new_state: string;
  timestamp: string;
  llm_impact?: string | null;
}

export interface KPIOut {
  total_assets: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  avg_age_months: number;
  assessed_count: number;
  pending_approval: number;
  approved_count: number;
  rejected_count: number;
  deferred_spend_inr: number;
  lifecycle_actions: Record<string, number>;
  action_percentages: Record<string, number>;
  departments: Record<string, number>;
  risk_by_department: Record<string, Record<string, number>>;
  co2_saved_kg: number;
  landfill_reduction_kg: number;
  carbon_offset_trees: number;
  material_recovery_pct: number;
}

export interface PolicySettings {
  age_threshold_months: number;
  ticket_threshold: number;
  thermal_threshold: number;
  smart_sector_threshold: number;
}

export interface GenerateRequest {
  count: number;
  department?: string;
  region?: string;
  auto_assess: boolean;
}

export interface GenerateResult {
  generated: number;
  assessed: number;
  asset_ids: string[];
  message: string;
}

export interface ModelInfo {
  model_version?: string;
  best_model?: string;
  test_metrics?: {
    auc_roc?: number;
    accuracy?: number;
    f1_macro?: number;
  };
  feature_importances?: Array<{ feature: string; importance: number }>;
}
