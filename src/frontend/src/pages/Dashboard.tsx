import { useEffect, useRef, useState } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
} from 'recharts';
import { Leaf, Recycle, Wrench, Package, RefreshCw, TreePine, AlertTriangle, Pause, Play } from 'lucide-react';
import { getKPIs, getModelInfo, generateDemo, type KPIOut, type ModelInfo } from '../services/api';
import KPICard from '../components/KPICard';

const REFRESH_INTERVAL_SEC = 30;

const ACTION_COLORS: Record<string, string> = {
  recycle:   '#ef4444',
  repair:    '#f97316',
  refurbish: '#eab308',
  redeploy:  '#3b82f6',
  resale:    '#22c55e',
};

const RISK_COLORS = { high: '#ef4444', medium: '#f97316', low: '#22c55e' };

export default function Dashboard() {
  const [kpis, setKpis] = useState<KPIOut | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [countdown, setCountdown] = useState(REFRESH_INTERVAL_SEC);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [k, m] = await Promise.all([getKPIs(), getModelInfo()]);
      setKpis(k);
      setModelInfo(m);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const resetCountdown = () => setCountdown(REFRESH_INTERVAL_SEC);

  // Auto-refresh effect
  useEffect(() => {
    if (autoRefresh) {
      resetCountdown();
      intervalRef.current = setInterval(() => {
        load();
        resetCountdown();
      }, REFRESH_INTERVAL_SEC * 1000);
      countdownRef.current = setInterval(() => {
        setCountdown(c => (c > 1 ? c - 1 : REFRESH_INTERVAL_SEC));
      }, 1000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [autoRefresh]);

  useEffect(() => { load(); }, []);

  const handleSeedDemo = async () => {
    setGenerating(true);
    await generateDemo({ count: 20, auto_assess: true }).catch(() => {});
    await load();
    resetCountdown();
    setGenerating(false);
  };

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-green-600" />
    </div>
  );

  const pieData = kpis ? Object.entries(kpis.lifecycle_actions).map(([name, value]) => ({ name, value })) : [];
  const riskData = kpis ? [
    { name: 'High', value: kpis.high_risk,   fill: RISK_COLORS.high   },
    { name: 'Medium', value: kpis.medium_risk, fill: RISK_COLORS.medium },
    { name: 'Low',  value: kpis.low_risk,    fill: RISK_COLORS.low    },
  ] : [];

  // Decision Drivers from model feature importances
  const driverData = modelInfo?.feature_importances
    ?.slice(0, 6)
    .map(f => ({ name: f.feature.replace(/_/g, ' '), importance: Math.round(f.importance * 100) }))
    ?? [];

  const hasData = kpis && kpis.total_assets > 0;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Fleet health overview & environmental impact</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Auto-refresh toggle */}
          <button
            onClick={() => setAutoRefresh(r => !r)}
            title={autoRefresh ? 'Pause auto-refresh' : 'Enable auto-refresh'}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium border transition-colors ${
              autoRefresh
                ? 'bg-indigo-50 border-indigo-200 text-indigo-700 hover:bg-indigo-100'
                : 'bg-gray-50 border-gray-200 text-gray-500 hover:bg-gray-100'
            }`}
          >
            {autoRefresh ? <Pause size={14} /> : <Play size={14} />}
            {autoRefresh ? (
              <span className="flex items-center gap-1">
                Auto <span className="tabular-nums bg-indigo-100 text-indigo-800 rounded px-1">{countdown}s</span>
              </span>
            ) : (
              'Auto-refresh off'
            )}
          </button>

          <button
            onClick={handleSeedDemo}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={16} className={generating ? 'animate-spin' : ''} />
            {generating ? 'Generating...' : 'Seed Demo Data'}
          </button>
        </div>
      </div>

      {!hasData ? (
        <div className="flex flex-col items-center justify-center py-24 text-gray-400">
          <Package size={48} className="mb-4 opacity-30" />
          <p className="text-lg font-medium">No data yet</p>
          <p className="text-sm mt-1">Click "Seed Demo Data" to generate a synthetic fleet</p>
        </div>
      ) : (
        <>
          {/* KPI strip — row 1 */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <KPICard
              label="Total Devices"
              value={kpis!.total_assets}
              sub={`${kpis!.assessed_count} assessed`}
              icon={<Package size={20} />}
            />
            <KPICard
              label="Recycle %"
              value={`${kpis!.action_percentages?.recycle ?? 0}%`}
              color="bg-red-50"
              icon={<Recycle size={20} className="text-red-400" />}
            />
            <KPICard
              label="Repair %"
              value={`${kpis!.action_percentages?.repair ?? 0}%`}
              color="bg-orange-50"
              icon={<Wrench size={20} className="text-orange-400" />}
            />
            <KPICard
              label="Refurbish %"
              value={`${kpis!.action_percentages?.refurbish ?? 0}%`}
              color="bg-yellow-50"
            />
            <KPICard
              label="Redeploy %"
              value={`${kpis!.action_percentages?.redeploy ?? 0}%`}
              color="bg-blue-50"
            />
            <KPICard
              label="CO₂ Saved"
              value={`${kpis!.co2_saved_kg} kg`}
              color="bg-green-50"
              icon={<Leaf size={20} className="text-green-500" />}
            />
          </div>

          {/* Row 2: action donut + decision drivers */}
          <div className="grid md:grid-cols-2 gap-4">
            {/* Action Distribution */}
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-gray-800">Action Distribution</h2>
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
                  + LLM insight
                </span>
              </div>
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={85}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {pieData.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={ACTION_COLORS[entry.name] ?? '#9ca3af'}
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 justify-center mt-2">
                {pieData.map((d) => (
                  <div key={d.name} className="flex items-center gap-1.5 text-xs text-gray-600">
                    <span
                      className="inline-block w-2.5 h-2.5 rounded-full"
                      style={{ background: ACTION_COLORS[d.name] ?? '#9ca3af' }}
                    />
                    <span className="capitalize">{d.name}</span>
                    <span className="text-gray-400">({d.value})</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Decision Drivers */}
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <h2 className="font-semibold text-gray-800 mb-3">Decision Drivers</h2>
              {driverData.length > 0 ? (
                <div className="h-52">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={driverData} layout="vertical" margin={{ left: 20, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} />
                      <YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v: number) => `${v}%`} />
                      <Bar dataKey="importance" fill="#6366f1" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-sm text-gray-400 mt-8 text-center">
                  Feature importances available after model inference
                </p>
              )}
            </div>
          </div>

          {/* Row 3: Risk segmentation + alert banner */}
          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <h2 className="font-semibold text-gray-800 mb-4">Risk &amp; Health Segmentation</h2>
              <div className="space-y-3">
                {riskData.map(({ name, value, fill }) => {
                  const pct = kpis!.total_assets > 0 ? (value / kpis!.total_assets) * 100 : 0;
                  return (
                    <div key={name}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="font-medium text-gray-700">{name} Risk</span>
                        <span className="text-gray-500">{value} devices ({pct.toFixed(1)}%)</span>
                      </div>
                      <div className="h-3 bg-gray-100 rounded-full">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{ width: `${pct}%`, background: fill }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
              <h2 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                <AlertTriangle size={16} className="text-amber-500" />
                Workflow Status
              </h2>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-amber-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-amber-700">{kpis!.pending_approval}</p>
                  <p className="text-xs text-amber-600 mt-0.5">Pending Approval</p>
                </div>
                <div className="bg-green-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-green-700">{kpis!.approved_count}</p>
                  <p className="text-xs text-green-600 mt-0.5">Approved</p>
                </div>
                <div className="bg-red-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-red-700">{kpis!.rejected_count}</p>
                  <p className="text-xs text-red-600 mt-0.5">Rejected</p>
                </div>
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-blue-700">
                    ₹{((kpis!.deferred_spend_inr ?? 0) / 100000).toFixed(1)}L
                  </p>
                  <p className="text-xs text-blue-600 mt-0.5">Deferred Spend</p>
                </div>
              </div>
            </div>
          </div>

          {/* Row 4: Environmental Impact */}
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl p-5 border border-green-100">
            <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Leaf size={18} className="text-green-600" />
              Environmental Impact
            </h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-3xl font-bold text-green-700">{kpis!.landfill_reduction_kg}<span className="text-base font-normal ml-1">kg</span></p>
                <p className="text-sm text-gray-600 mt-1">Landfill Reduction</p>
                <p className="text-xs text-gray-400">e-waste diverted</p>
              </div>
              <div className="text-center border-x border-green-200">
                <p className="text-3xl font-bold text-green-700 flex items-center justify-center gap-1">
                  <TreePine size={24} />{kpis!.carbon_offset_trees}
                </p>
                <p className="text-sm text-gray-600 mt-1">Trees Equivalent</p>
                <p className="text-xs text-gray-400">{kpis!.co2_saved_kg} kg CO₂ offset</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-green-700">{kpis!.material_recovery_pct.toFixed(0)}<span className="text-base font-normal ml-0.5">%</span></p>
                <p className="text-sm text-gray-600 mt-1">Material Recovery</p>
                <p className="text-xs text-gray-400">rare earth metals</p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
