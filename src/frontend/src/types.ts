export type RiskLabel = 'high' | 'medium' | 'low'
export type FinalAction = 'RECYCLE' | 'REPAIR' | 'REFURBISH' | 'RESALE' | 'REDEPLOY'

export interface Scenario {
  // internal
  _name: string
  _expected_action: FinalAction
  _expected_risk_score: number
  // device fields
  asset_id: string
  device_type: string
  brand: string
  department: string
  region: string
  usage_type: string
  os: string
  age_in_months: number
  model_year: number
  battery_health_percent: number
  battery_cycles: number
  smart_sectors_reallocated: number
  thermal_events_count: number
  overheating_issues: string
  daily_usage_hours: number
  performance_rating: number
  total_incidents: number
  critical_incidents: number
  high_incidents: number
  medium_incidents: number
  low_incidents: number
  avg_resolution_time_hours: number
  data_completeness: number
}

export interface MLResult {
  risk_label: RiskLabel
  risk_score: number
  ml_available: boolean
  model_version?: string
}

export interface PolicyResult {
  classification: RiskLabel
  recommended_action: FinalAction
  supporting_signals: string[]
  policy_version?: string
}

export interface IstmTask {
  title: string
  priority: string
  assigned_team: string
  description: string
  checklist: string[]
}

export interface LLMResult {
  explanation: string
  itsm_task: IstmTask | string | null
  llm_available: boolean
}

export interface AnalysisResult {
  asset_id: string
  final_action: FinalAction
  confidence_score: number
  ml_result: MLResult
  policy_result: PolicyResult
  llm_result: LLMResult
}
