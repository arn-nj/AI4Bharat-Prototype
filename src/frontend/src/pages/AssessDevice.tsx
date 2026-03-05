import { useState } from 'react';
import { createAsset, assessAsset, type AssetCreate, type AssessmentResultOut } from '../services/api';
import ActionBadge from '../components/ActionBadge';
import RiskBadge from '../components/RiskBadge';
import ConfidenceBar from '../components/ConfidenceBar';

const DEPARTMENTS = ['Engineering', 'HR', 'Finance', 'Operations', 'IT', 'Sales', 'Marketing', 'Legal'];
const REGIONS     = ['North', 'South', 'East', 'West', 'Central'];
const DEVICES     = ['Laptop', 'Desktop', 'Server', 'Tablet', 'Workstation'];

const DEFAULT_FORM: AssetCreate = {
  device_type: 'Laptop',
  department: 'IT',
  region: 'North',
  brand: '',
  model_year: 2021,
  total_incidents: undefined,
  critical_incidents: undefined,
  battery_cycles: undefined,
  thermal_events_count: undefined,
  smart_sectors_reallocated: undefined,
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
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Assess Device</h1>
        <p className="text-sm text-gray-500 mt-0.5">Submit device telemetry and ticket data for AI-powered risk assessment</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Form */}
        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
          <h2 className="font-semibold text-gray-700">Device Details</h2>

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
              <label className={labelClass}>Department *</label>
              <select className={inputClass} value={form.department} onChange={e => set('department', e.target.value)}>
                {DEPARTMENTS.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>Region *</label>
              <select className={inputClass} value={form.region} onChange={e => set('region', e.target.value)}>
                {REGIONS.map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className={labelClass}>Model Year</label>
            <input type="number" className={inputClass} value={form.model_year ?? ''} onChange={e => set('model_year', Number(e.target.value))} min={2000} max={2025} />
          </div>

          <h2 className="font-semibold text-gray-700 pt-2">Telemetry (optional)</h2>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Battery Cycles</label>
              <input type="number" className={inputClass} value={form.battery_cycles ?? ''} onChange={e => set('battery_cycles', e.target.value ? Number(e.target.value) : undefined)} />
            </div>
            <div>
              <label className={labelClass}>Thermal Events</label>
              <input type="number" className={inputClass} value={form.thermal_events_count ?? ''} onChange={e => set('thermal_events_count', e.target.value ? Number(e.target.value) : undefined)} />
            </div>
            <div>
              <label className={labelClass}>SMART Sectors</label>
              <input type="number" className={inputClass} value={form.smart_sectors_reallocated ?? ''} onChange={e => set('smart_sectors_reallocated', e.target.value ? Number(e.target.value) : undefined)} />
            </div>
            <div>
              <label className={labelClass}>Total Incidents</label>
              <input type="number" className={inputClass} value={form.total_incidents ?? ''} onChange={e => set('total_incidents', e.target.value ? Number(e.target.value) : undefined)} />
            </div>
            <div>
              <label className={labelClass}>Critical Incidents</label>
              <input type="number" className={inputClass} value={form.critical_incidents ?? ''} onChange={e => set('critical_incidents', e.target.value ? Number(e.target.value) : undefined)} />
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
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-3">
                <h2 className="font-semibold text-gray-700">Risk Assessment</h2>
                <div className="flex items-center gap-3">
                  <RiskBadge level={result.risk.risk_level} />
                  <span className="text-sm text-gray-500">Score: {(result.risk.risk_score * 100).toFixed(0)}%</span>
                </div>
                <ConfidenceBar score={result.risk.risk_score} band={result.risk.confidence_band} />
                <p className="text-xs text-gray-400">Mode: {result.risk.eval_mode}</p>
                {result.risk.ml_scores && (
                  <div className="bg-purple-50 rounded-lg p-3 text-xs text-purple-700">
                    <p className="font-semibold mb-1">ML Model: {result.risk.ml_scores.ml_risk_label}</p>
                    <p>p(high)={result.risk.ml_scores.p_high.toFixed(3)}  p(med)={result.risk.ml_scores.p_medium.toFixed(3)}  p(low)={result.risk.ml_scores.p_low.toFixed(3)}</p>
                  </div>
                )}
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
