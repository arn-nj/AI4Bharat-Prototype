import { useState } from 'react';
import { createAsset, assessAsset, type AssetCreate, type AssessmentResultOut } from '../services/api';
import ActionBadge from '../components/ActionBadge';
import RiskBadge from '../components/RiskBadge';
import ConfidenceBar from '../components/ConfidenceBar';

const RISK_COLORS: Record<string, string> = {
  high:   'bg-red-50 border-red-200 text-red-700',
  medium: 'bg-orange-50 border-orange-200 text-orange-700',
  low:    'bg-green-50 border-green-200 text-green-700',
};

const DEPARTMENTS  = ['Engineering', 'HR', 'Finance', 'Operations', 'IT', 'Sales', 'Marketing', 'Legal'];
const OFFICE_LOCATIONS = [
  'Mumbai', 'Bengaluru', 'Chennai', 'Hyderabad', 'Delhi NCR',
  'Pune', 'Kolkata', 'Ahmedabad', 'Kochi', 'Noida',
];
const DEVICES = [
  'Laptop', 'Desktop', 'Server', 'Tablet', 'Workstation',
  'Printer', 'Network Device', 'Mobile Phone', 'Monitor', 'Projector',
];
const OS_OPTIONS   = ['Windows 11', 'Windows 10', 'macOS 14', 'Ubuntu 22.04', 'ChromeOS', 'Android 14', 'iOS 17'];
const USAGE_TYPES  = ['Standard', 'Development', 'Creative', 'Intensive', 'Light'];

const DEFAULT_FORM: AssetCreate = {
  device_type: 'Laptop',
  department: 'IT',
  region: 'Bengaluru',
  brand: '',
  model_year: new Date().getFullYear(),
  os: 'Windows 11',
  usage_type: 'Standard',
};

export default function AssessDevice() {
  const [form, setForm] = useState<AssetCreate>(DEFAULT_FORM);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AssessmentResultOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof AssetCreate, v: unknown) =>
    setForm(prev => ({ ...prev, [k]: v === '' ? undefined : v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const asset = await createAsset(form);
      const assessment = await assessAsset(asset.asset_id);
      setResult(assessment);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Assessment failed');
    } finally {
      setLoading(false);
    }
  };

  const labelClass = 'block text-xs font-medium text-gray-600 mb-1';
  const inputClass = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500';

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Assess Device</h1>
        <p className="text-sm text-gray-500 mt-0.5">Submit device details and telemetry for AI-powered risk assessment</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">

          {/* ── Identity & Usage ─────────────────────── */}
          <h2 className="font-semibold text-gray-700 text-sm uppercase tracking-wide text-gray-400">Identity &amp; Usage</h2>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Device Type *</label>
              <select className={inputClass} value={form.device_type} onChange={e => set('device_type', e.target.value)}>
                {DEVICES.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>Brand</label>
              <input className={inputClass} value={form.brand ?? ''} onChange={e => set('brand', e.target.value)} placeholder="Dell, HP, Apple…" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Serial Number</label>
              <input className={inputClass} value={form.serial_number ?? ''} onChange={e => set('serial_number', e.target.value)} placeholder="e.g. HP20245B3A2F" />
            </div>
            <div>
              <label className={labelClass}>Model Name</label>
              <input className={inputClass} value={form.model_name ?? ''} onChange={e => set('model_name', e.target.value)} placeholder="e.g. EliteBook 840 G9" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Department *</label>
              <select className={inputClass} value={form.department} onChange={e => set('department', e.target.value)}>
                {DEPARTMENTS.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>State / Office Location *</label>
              <select className={inputClass} value={form.region} onChange={e => set('region', e.target.value)}>
                {OFFICE_LOCATIONS.map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>OS</label>
              <select className={inputClass} value={form.os ?? ''} onChange={e => set('os', e.target.value)}>
                <option value="">Select…</option>
                {OS_OPTIONS.map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>Usage Type</label>
              <select className={inputClass} value={form.usage_type ?? ''} onChange={e => set('usage_type', e.target.value)}>
                <option value="">Select…</option>
                {USAGE_TYPES.map(u => <option key={u}>{u}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={labelClass}>Model Year</label>
              <input type="number" className={inputClass} value={form.model_year ?? ''} onChange={e => set('model_year', Number(e.target.value))} min={2000} max={new Date().getFullYear()} />
            </div>
            <div>
              <label className={labelClass}>Daily Usage (hrs)</label>
              <input type="number" className={inputClass} value={form.daily_usage_hours ?? ''} onChange={e => set('daily_usage_hours', e.target.value ? Number(e.target.value) : undefined)} min={0} max={24} step={0.5} />
            </div>
            <div>
              <label className={labelClass}>Performance (1-5)</label>
              <input type="number" className={inputClass} value={form.performance_rating ?? ''} onChange={e => set('performance_rating', e.target.value ? Number(e.target.value) : undefined)} min={1} max={5} />
            </div>
          </div>

          {/* ── Hardware Health ───────────────────────── */}
          <h2 className="font-semibold text-gray-700 text-sm uppercase tracking-wide text-gray-400 pt-2">Hardware Health &amp; Telemetry</h2>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Battery Health (%)</label>
              <input type="number" className={inputClass} value={form.battery_health_pct ?? ''} onChange={e => set('battery_health_pct', e.target.value ? Number(e.target.value) : undefined)} min={0} max={100} />
            </div>
            <div>
              <label className={labelClass}>Battery Cycles</label>
              <input type="number" className={inputClass} value={form.battery_cycles ?? ''} onChange={e => set('battery_cycles', e.target.value ? Number(e.target.value) : undefined)} min={0} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>SMART Sectors</label>
              <input type="number" className={inputClass} value={form.smart_sectors_reallocated ?? ''} onChange={e => set('smart_sectors_reallocated', e.target.value ? Number(e.target.value) : undefined)} min={0} />
            </div>
            <div>
              <label className={labelClass}>Thermal Events (90d)</label>
              <input type="number" className={inputClass} value={form.thermal_events_count ?? ''} onChange={e => set('thermal_events_count', e.target.value ? Number(e.target.value) : undefined)} min={0} />
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer select-none text-sm text-gray-600">
              <input
                type="checkbox"
                checked={form.overheating_issues ?? false}
                onChange={e => set('overheating_issues', e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 text-green-600 focus:ring-green-500"
              />
              Overheating Issues Reported
            </label>
          </div>

          {/* ── Incidents ─────────────────────────────── */}
          <h2 className="font-semibold text-gray-700 text-sm uppercase tracking-wide text-gray-400 pt-2">Incidents (90d)</h2>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Total Incidents</label>
              <input type="number" className={inputClass} value={form.total_incidents ?? ''} onChange={e => set('total_incidents', e.target.value ? Number(e.target.value) : undefined)} min={0} />
            </div>
            <div>
              <label className={labelClass}>Critical</label>
              <input type="number" className={inputClass} value={form.critical_incidents ?? ''} onChange={e => set('critical_incidents', e.target.value ? Number(e.target.value) : undefined)} min={0} />
            </div>
            <div>
              <label className={labelClass}>High</label>
              <input type="number" className={inputClass} value={form.high_incidents ?? ''} onChange={e => set('high_incidents', e.target.value ? Number(e.target.value) : undefined)} min={0} />
            </div>
            <div>
              <label className={labelClass}>Medium</label>
              <input type="number" className={inputClass} value={form.medium_incidents ?? ''} onChange={e => set('medium_incidents', e.target.value ? Number(e.target.value) : undefined)} min={0} />
            </div>
            <div>
              <label className={labelClass}>Low</label>
              <input type="number" className={inputClass} value={form.low_incidents ?? ''} onChange={e => set('low_incidents', e.target.value ? Number(e.target.value) : undefined)} min={0} />
            </div>
            <div>
              <label className={labelClass}>Avg Resolution (hrs)</label>
              <input type="number" className={inputClass} value={form.avg_resolution_time_hours ?? ''} onChange={e => set('avg_resolution_time_hours', e.target.value ? Number(e.target.value) : undefined)} min={0} step={0.5} />
            </div>
          </div>

          {error && <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-2.5 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? 'Analysing…' : 'Analyse Device'}
          </button>
        </form>

        {/* Result */}
        <div className="space-y-4">
          {result ? (
            <>
              {/* ML vs LLM dual prediction */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-3">
                <h2 className="font-semibold text-gray-700">Model Predictions</h2>
                <div className="grid grid-cols-2 gap-3">
                  {/* ML model */}
                  <div className="rounded-lg border border-purple-200 bg-purple-50 p-3 space-y-1.5">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-purple-500">ML Model</p>
                    <RiskBadge level={result.risk.risk_level as 'high' | 'medium' | 'low'} />
                    <ActionBadge action={result.recommendation.action as string} size="sm" />
                    {result.risk.ml_scores && (
                      <p className="text-[10px] text-purple-600 leading-tight">
                        p(H)={result.risk.ml_scores.p_high.toFixed(2)} p(M)={result.risk.ml_scores.p_medium.toFixed(2)} p(L)={result.risk.ml_scores.p_low.toFixed(2)}
                      </p>
                    )}
                    <p className="text-[10px] text-purple-400">{result.risk.eval_mode}</p>
                  </div>
                  {/* LLM prediction */}
                  <div className={`rounded-lg border p-3 space-y-1.5 ${
                    result.llm_prediction
                      ? (RISK_COLORS[result.llm_prediction.risk_level] ?? 'bg-gray-50 border-gray-200 text-gray-700')
                      : 'bg-gray-50 border-dashed border-gray-200'
                  }`}>
                    <p className="text-[11px] font-semibold uppercase tracking-wide opacity-60">LLM (Qwen3)</p>
                    {result.llm_prediction ? (
                      <>
                        <RiskBadge level={result.llm_prediction.risk_level as 'high' | 'medium' | 'low'} />
                        <ActionBadge action={result.llm_prediction.action} size="sm" />
                        <p className="text-[10px] italic opacity-80 leading-tight">{result.llm_prediction.reasoning}</p>
                        {result.llm_prediction.agrees_with_ml !== undefined && (
                          <p className={`text-[10px] font-medium ${result.llm_prediction.agrees_with_ml ? 'text-green-600' : 'text-amber-600'}`}>
                            {result.llm_prediction.agrees_with_ml ? '✓ Agrees with ML' : '⚠ Differs from ML'}
                          </p>
                        )}
                      </>
                    ) : (
                      <p className="text-xs text-gray-400 mt-2">Unavailable</p>
                    )}
                  </div>
                </div>
                <ConfidenceBar score={result.risk.risk_score} band={result.risk.confidence_band} />
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-3">
                <h2 className="font-semibold text-gray-700">Recommendation</h2>
                <ActionBadge action={result.recommendation.action} />
                <p className="text-sm text-gray-600 leading-relaxed">{result.recommendation.rationale}</p>
                {result.recommendation.itsm_task && (
                  <details className="mt-2">
                    <summary className="text-xs text-blue-600 cursor-pointer hover:underline">View ITSM Task</summary>
                    <pre className="mt-2 text-xs bg-gray-50 rounded p-2 overflow-auto max-h-40">
                      {JSON.stringify(result.recommendation.itsm_task, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </>
          ) : (
            <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 h-64 flex items-center justify-center text-gray-400 text-sm">
              Assessment results will appear here
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
