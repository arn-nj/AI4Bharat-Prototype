import { useEffect, useRef, useState } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
} from 'recharts';
import { Leaf, Package, RefreshCw, TreePine, Pause, Play, BrainCircuit, Clock, ChevronDown, ChevronUp, ShieldAlert, Bell, IndianRupee, ScanLine } from 'lucide-react';
import { getKPIs, getModelInfo, generateDemo, getFleetNarrative, type KPIOut, type ModelInfo } from '../services/api';


const REFRESH_INTERVAL_SEC = 30;

// Module-level cache — survives component remounts during navigation
let _narrativeCache = '';
let _narrativeCacheFleetSize = -1;

const ACTION_COLORS: Record<string, string> = {
  recycle:   '#ef4444',
  repair:    '#f97316',
  refurbish: '#eab308',
  redeploy:  '#3b82f6',
  resale:    '#22c55e',
};

const RISK_COLORS = { high: '#ef4444', medium: '#f97316', low: '#22c55e' };
const DEVICE_PALETTE = ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

export default function Dashboard() {
  const [kpis, setKpis] = useState<KPIOut | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [narrative, setNarrative] = useState<string>('');
  const [narrativeLoading, setNarrativeLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [countdown, setCountdown] = useState(REFRESH_INTERVAL_SEC);
  const [narrativeOpen, setNarrativeOpen] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Track last fleet size so we only regenerate narrative when fleet changes
  const narrativeFleetSizeRef = useRef<number>(-1);

  /** Lightweight KPI-only refresh — does NOT re-trigger LLM narrative */
  const loadKPIs = async () => {
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

  /** Fetch narrative only when fleet actually changes size */
  const refreshNarrative = async (totalAssets: number, force = false) => {
    if (!force && _narrativeCacheFleetSize === totalAssets && _narrativeCache) {
      setNarrative(_narrativeCache);
      return;
    }
    if (totalAssets === 0) { setNarrative(''); return; }
    narrativeFleetSizeRef.current = totalAssets;
    setNarrativeLoading(true);
    getFleetNarrative()
      .then(r => {
        const text = r.narrative ?? '';
        _narrativeCache = text;
        _narrativeCacheFleetSize = totalAssets;
        setNarrative(text);
        setNarrativeOpen(true);
      })
      .catch(() => {})
      .finally(() => setNarrativeLoading(false));
  };

  /** Initial full load */
  const load = async () => {
    setLoading(true);
    try {
      const [k, m] = await Promise.all([getKPIs(), getModelInfo()]);
      setKpis(k);
      setModelInfo(m);
      if (k) refreshNarrative(k.total_assets);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const resetCountdown = () => setCountdown(REFRESH_INTERVAL_SEC);

  // Auto-refresh effect — only refreshes KPIs, NOT the narrative
  useEffect(() => {
    if (autoRefresh) {
      resetCountdown();
      intervalRef.current = setInterval(() => {
        loadKPIs();
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

  // Risk by Region stacked bar data
  const riskByRegionData = kpis
    ? Object.entries(kpis.risk_by_region).map(([region, counts]) => ({
        region,
        high: counts.high ?? 0,
        medium: counts.medium ?? 0,
        low: counts.low ?? 0,
      }))
    : [];

  // Device type breakdown data
  const deviceTypeData = kpis
    ? Object.entries(kpis.device_type_counts)
        .sort((a, b) => b[1] - a[1])
        .map(([name, count]) => ({ name, count }))
    : [];

  // Decision Drivers from model feature importances
  const driverData = modelInfo?.feature_importances
    ?.slice(0, 6)
    .map(f => ({ name: f.feature.replace(/_/g, ' '), importance: Math.round(f.importance * 100) }))
    ?? [];

  const assessedPct = kpis && kpis.total_assets > 0
    ? Math.round((kpis.assessed_count / kpis.total_assets) * 100)
    : 0;
  const hasData = kpis && kpis.total_assets > 0;
  const approvalTotal = kpis ? kpis.approved_count + kpis.pending_approval + kpis.rejected_count : 1;

  return (
    <div className="h-full flex flex-col overflow-hidden p-3 gap-2">
      {/* ── Header ── */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-xs text-gray-500">Fleet health overview &amp; environmental impact</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(r => !r)}
            title={autoRefresh ? 'Pause auto-refresh' : 'Enable auto-refresh'}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              autoRefresh
                ? 'bg-indigo-50 border-indigo-200 text-indigo-700 hover:bg-indigo-100'
                : 'bg-gray-50 border-gray-200 text-gray-500 hover:bg-gray-100'
            }`}
          >
            {autoRefresh ? <Pause size={12} /> : <Play size={12} />}
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
            className="flex items-center gap-2 px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={13} className={generating ? 'animate-spin' : ''} />
            {generating ? 'Generating...' : 'Seed Demo Data'}
          </button>
        </div>
      </div>

      {!hasData ? (
        <div className="flex flex-col items-center justify-center flex-1 text-gray-400">
          <Package size={40} className="mb-3 opacity-30" />
          <p className="text-base font-medium">No data yet</p>
          <p className="text-sm mt-1">Click "Seed Demo Data" to generate a synthetic fleet</p>
        </div>
      ) : (
        <>
          {/* ── KPI Strip — 6 purposeful metrics, zero duplication ── */}
          <div className="grid grid-cols-3 md:grid-cols-6 gap-2 flex-shrink-0">

            {/* 1. Total Devices */}
            <div className="bg-white rounded-lg px-3 py-2 shadow-md border border-gray-100 flex items-center gap-2.5 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-150">
              <div className="w-8 h-8 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <Package size={15} className="text-gray-600" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-gray-500 uppercase tracking-wide truncate">Total Devices</p>
                <p className="text-xl font-bold leading-tight">{kpis!.total_assets}</p>
                <p className="text-[10px] text-gray-400">{kpis!.assessed_count} assessed</p>
              </div>
            </div>

            {/* 2. Avg Fleet Age */}
            <div className="bg-indigo-50 rounded-lg px-3 py-2 shadow-md border border-indigo-100 flex items-center gap-2.5 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-150">
              <div className="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <Clock size={15} className="text-indigo-600" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-indigo-600 uppercase tracking-wide truncate">Fleet Age</p>
                <p className="text-xl font-bold text-indigo-800 leading-tight">{kpis!.avg_age_months}<span className="text-xs font-normal ml-0.5">mo</span></p>
                <p className="text-[10px] text-indigo-400">{(kpis!.avg_age_months / 12).toFixed(1)} yr avg</p>
              </div>
            </div>

            {/* 3. High Risk — alert state */}
            <div className={`rounded-lg px-3 py-2 shadow-md border flex items-center gap-2.5 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-150 ${
              kpis!.high_risk > 0 ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-100'
            }`}>
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                kpis!.high_risk > 0 ? 'bg-red-100' : 'bg-gray-100'
              }`}>
                <ShieldAlert size={15} className={kpis!.high_risk > 0 ? 'text-red-600' : 'text-gray-400'} />
              </div>
              <div className="min-w-0">
                <p className={`text-[10px] uppercase tracking-wide truncate ${kpis!.high_risk > 0 ? 'text-red-600' : 'text-gray-500'}`}>High Risk</p>
                <p className={`text-xl font-bold leading-tight ${kpis!.high_risk > 0 ? 'text-red-700' : 'text-gray-700'}`}>{kpis!.high_risk}</p>
                <p className={`text-[10px] ${kpis!.high_risk > 0 ? 'text-red-400' : 'text-gray-400'}`}>{kpis!.high_risk > 0 ? 'need attention' : 'all clear ✓'}</p>
              </div>
            </div>

            {/* 4. Assessment Coverage — progress signal */}
            <div className={`rounded-lg px-3 py-2 shadow-md border flex items-center gap-2.5 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-150 ${
              assessedPct < 60 ? 'bg-amber-50 border-amber-100' : 'bg-teal-50 border-teal-100'
            }`}>
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                assessedPct < 60 ? 'bg-amber-100' : 'bg-teal-100'
              }`}>
                <ScanLine size={15} className={assessedPct < 60 ? 'text-amber-600' : 'text-teal-600'} />
              </div>
              <div className="min-w-0">
                <p className={`text-[10px] uppercase tracking-wide truncate ${assessedPct < 60 ? 'text-amber-600' : 'text-teal-600'}`}>Assessed</p>
                <p className={`text-xl font-bold leading-tight ${assessedPct < 60 ? 'text-amber-700' : 'text-teal-700'}`}>{assessedPct}<span className="text-xs font-normal ml-0.5">%</span></p>
                <p className={`text-[10px] ${assessedPct < 60 ? 'text-amber-400' : 'text-teal-400'}`}>{kpis!.assessed_count}/{kpis!.total_assets} devices</p>
              </div>
            </div>

            {/* 5. Pending Review — action signal */}
            <div className="bg-amber-50 rounded-lg px-3 py-2 shadow-md border border-amber-100 flex items-center gap-2.5 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-150">
              <div className="w-8 h-8 bg-amber-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <Bell size={15} className="text-amber-600" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-amber-600 uppercase tracking-wide truncate">Pending Review</p>
                <p className="text-xl font-bold text-amber-700 leading-tight">{kpis!.pending_approval}</p>
                <p className="text-[10px] text-amber-400">awaiting decisions</p>
              </div>
            </div>

            {/* 6. Deferred Spend — ROI metric */}
            <div className="bg-blue-50 rounded-lg px-3 py-2 shadow-md border border-blue-100 flex items-center gap-2.5 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-150">
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <IndianRupee size={15} className="text-blue-600" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-blue-600 uppercase tracking-wide truncate">Spend Saved</p>
                <p className="text-xl font-bold text-blue-700 leading-tight">₹{((kpis!.deferred_spend_inr ?? 0) / 100000).toFixed(1)}<span className="text-xs font-normal ml-0.5">L</span></p>
                <p className="text-[10px] text-blue-400">deferred procurement</p>
              </div>
            </div>
          </div>

          {/* ── AI Fleet Summary — collapsible ── */}
          {(narrative || narrativeLoading) && (
            <div className="flex-shrink-0 bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-100 rounded-lg overflow-hidden">
              <button
                className="w-full px-3 py-1.5 flex items-center gap-2 text-left"
                onClick={() => !narrativeLoading && setNarrativeOpen(o => !o)}
              >
                <BrainCircuit size={13} className="text-indigo-500 flex-shrink-0" />
                <span className="text-[10px] font-semibold text-indigo-600 uppercase tracking-wide flex-shrink-0">AI Fleet Summary</span>
                {narrativeLoading ? (
                  <span className="text-xs text-gray-500 flex items-center gap-1.5 flex-1">
                    <span className="w-2 h-2 rounded-full border border-indigo-400 border-t-transparent animate-spin inline-block" />
                    Generating fleet analysis…
                  </span>
                ) : (
                  <span className="text-[10px] text-indigo-400 flex-1">
                    {narrativeOpen ? 'Click to collapse' : 'Fleet analysis ready · click to expand'}
                  </span>
                )}
                <span className="flex items-center gap-1 flex-shrink-0" onClick={e => e.stopPropagation()}>
                  <button
                    onClick={() => kpis && refreshNarrative(kpis.total_assets, true)}
                    disabled={narrativeLoading}
                    className="text-indigo-400 hover:text-indigo-700 disabled:opacity-40"
                    title="Refresh"
                  >
                    <RefreshCw size={11} className={narrativeLoading ? 'animate-spin' : ''} />
                  </button>
                </span>
                {!narrativeLoading && (narrativeOpen
                  ? <ChevronUp size={13} className="text-indigo-400 flex-shrink-0" />
                  : <ChevronDown size={13} className="text-indigo-400 flex-shrink-0" />
                )}
              </button>
              {narrativeOpen && !narrativeLoading && narrative && (
                <div className="px-3 pb-2.5 border-t border-indigo-100">
                  <p className="text-xs text-gray-700 leading-relaxed pt-2">{narrative}</p>
                </div>
              )}
            </div>
          )}

          {/* ── Chart Grid ── */}
          <div className="flex-1 min-h-0 flex flex-col gap-2 overflow-hidden">

            {/* Row 1 — Risk intelligence */}
            <div className="grid grid-cols-3 gap-2 flex-[3_1_0%] min-h-0">

              {/* Risk Distribution donut — high risk as centrepiece */}
              <div className="bg-white rounded-xl p-3 shadow-md border border-gray-100 flex flex-col min-h-0 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-150">
                <h2 className="text-xs font-semibold text-gray-800 mb-1 flex-shrink-0">Risk Distribution</h2>
                <div className="relative flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={riskData}
                        cx="50%" cy="50%"
                        innerRadius="42%" outerRadius="68%"
                        paddingAngle={2} dataKey="value"
                        startAngle={90} endAngle={-270}
                      >
                        {riskData.map(({ fill }, i) => <Cell key={i} fill={fill} />)}
                      </Pie>
                      <Tooltip formatter={(v: number) => `${v} devices`} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="text-center leading-none">
                      <p className={`text-2xl font-extrabold ${kpis!.high_risk > 0 ? 'text-red-600' : 'text-green-600'}`}>{kpis!.high_risk}</p>
                      <p className="text-[9px] text-gray-500 mt-0.5">high risk</p>
                    </div>
                  </div>
                </div>
                <div className="flex justify-center gap-3 flex-shrink-0 mt-1">
                  {riskData.map(({ name, value, fill }) => (
                    <div key={name} className="flex items-center gap-1 text-[10px] text-gray-600">
                      <span className="w-2 h-2 rounded-full inline-block flex-shrink-0" style={{ background: fill }} />
                      {name} ({value})
                    </div>
                  ))}
                </div>
              </div>

              {/* Risk by Region */}
              <div className="bg-white rounded-xl p-3 shadow-md border border-gray-100 flex flex-col min-h-0 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-150">
                <h2 className="text-xs font-semibold text-gray-800 mb-1 flex-shrink-0">Risk by Region</h2>
                {riskByRegionData.length > 0 ? (
                  <div className="flex-1 min-h-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={riskByRegionData} margin={{ left: 0, right: 8 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="region" tick={{ fontSize: 9 }} />
                        <YAxis tick={{ fontSize: 9 }} allowDecimals={false} />
                        <Tooltip />
                        <Legend wrapperStyle={{ fontSize: 9 }} />
                        <Bar dataKey="high" stackId="a" name="High" fill={RISK_COLORS.high} />
                        <Bar dataKey="medium" stackId="a" name="Medium" fill={RISK_COLORS.medium} />
                        <Bar dataKey="low" stackId="a" name="Low" fill={RISK_COLORS.low} radius={[3, 3, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 flex-1 flex items-center justify-center">No region data</p>
                )}
              </div>

              {/* Device Mix donut */}
              <div className="bg-white rounded-xl p-3 shadow-md border border-gray-100 flex flex-col min-h-0 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-150">
                <h2 className="text-xs font-semibold text-gray-800 mb-1 flex-shrink-0">Device Mix</h2>
                {deviceTypeData.length > 0 ? (
                  <>
                    <div className="flex-1 min-h-0">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie data={deviceTypeData} cx="50%" cy="50%" innerRadius="38%" outerRadius="65%" paddingAngle={2} dataKey="count">
                            {deviceTypeData.map((_, i) => <Cell key={i} fill={DEVICE_PALETTE[i % DEVICE_PALETTE.length]} />)}
                          </Pie>
                          <Tooltip formatter={(v: number) => `${v} devices`} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="flex flex-wrap gap-x-2 gap-y-0.5 justify-center flex-shrink-0">
                      {deviceTypeData.map((d, i) => (
                        <div key={d.name} className="flex items-center gap-1 text-[10px] text-gray-600">
                          <span className="w-2 h-2 rounded-full inline-block flex-shrink-0" style={{ background: DEVICE_PALETTE[i % DEVICE_PALETTE.length] }} />
                          {d.name} ({d.count})
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="text-xs text-gray-400 flex-1 flex items-center justify-center">No device data</p>
                )}
              </div>
            </div>

            {/* Row 2 — Actions, decision intelligence, workflow */}
            <div className="grid grid-cols-3 gap-2 flex-[3_1_0%] min-h-0">

              {/* Circular Economy Actions — donut + % breakdown side by side */}
              <div className="bg-white rounded-xl p-3 shadow-md border border-gray-100 flex flex-col min-h-0 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-150">
                <div className="flex items-center justify-between mb-1 flex-shrink-0">
                  <h2 className="text-xs font-semibold text-gray-800">Asset Disposition</h2>
                  <span className="text-[10px] text-gray-400">{kpis!.assessed_count} assessed</span>
                </div>
                <div className="flex-1 min-h-0 flex gap-2 overflow-hidden">
                  <div className="flex-1 min-w-0 min-h-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={pieData} cx="50%" cy="50%" innerRadius="38%" outerRadius="70%" paddingAngle={3} dataKey="value">
                          {pieData.map((entry) => <Cell key={entry.name} fill={ACTION_COLORS[entry.name] ?? '#9ca3af'} />)}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex flex-col justify-center gap-2 flex-shrink-0 pr-1" style={{ minWidth: 88 }}>
                    {pieData.map((d) => (
                      <div key={d.name} className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: ACTION_COLORS[d.name] ?? '#9ca3af' }} />
                        <span className="text-[10px] text-gray-600 capitalize flex-1">{d.name}</span>
                        <span className="text-[10px] font-bold tabular-nums" style={{ color: ACTION_COLORS[d.name] ?? '#9ca3af' }}>
                          {(kpis!.action_percentages as Record<string, number>)?.[d.name] ?? 0}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Decision Drivers */}
              <div className="bg-white rounded-xl p-3 shadow-md border border-gray-100 flex flex-col min-h-0 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-150">
                <div className="flex items-center justify-between mb-1 flex-shrink-0">
                  <h2 className="text-xs font-semibold text-gray-800">Decision Drivers</h2>
                  <span className="text-[10px] text-gray-400 italic">trained model</span>
                </div>
                {driverData.length > 0 ? (
                  <div className="flex-1 min-h-0">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={driverData} layout="vertical" margin={{ left: 0, right: 12 }}>
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                        <XAxis type="number" domain={[0, 100]} unit="%" tick={{ fontSize: 9 }} />
                        <YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 9 }} />
                        <Tooltip formatter={(v: number) => `${v}%`} />
                        <Bar dataKey="importance" fill="#6366f1" radius={[0, 3, 3, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 flex-1 flex items-center justify-center text-center px-2">Feature importances available after model inference</p>
                )}
              </div>

              {/* Approval Workflow — progress bars, no duplication with KPI strip */}
              <div className="bg-white rounded-xl p-3 shadow-md border border-gray-100 flex flex-col min-h-0 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-150">
                <h2 className="text-xs font-semibold text-gray-800 mb-2 flex items-center gap-1.5 flex-shrink-0">
                  <Bell size={12} className="text-amber-500" />
                  Approval Workflow
                </h2>
                <div className="flex-1 flex flex-col justify-around gap-1 overflow-hidden">
                  {([
                    { label: 'Approved', value: kpis!.approved_count,   color: '#22c55e', text: 'text-green-700' },
                    { label: 'Pending',  value: kpis!.pending_approval, color: '#f59e0b', text: 'text-amber-700' },
                    { label: 'Rejected', value: kpis!.rejected_count,   color: '#ef4444', text: 'text-red-700'   },
                  ] as const).map(({ label, value, color, text }) => {
                    const pct = approvalTotal > 0 ? Math.round((value / approvalTotal) * 100) : 0;
                    return (
                      <div key={label}>
                        <div className="flex justify-between text-[10px] mb-1">
                          <span className="font-medium text-gray-700">{label}</span>
                          <span className={`font-bold tabular-nums ${text}`}>{value} <span className="font-normal text-gray-400">({pct}%)</span></span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Row 3 — Environmental Impact (mission row, full width) */}
            <div className="flex-[2_1_0%] min-h-0 bg-gradient-to-r from-green-50 via-emerald-50 to-teal-50 rounded-xl px-5 py-3 border border-green-100 flex flex-col justify-between">
              <div className="flex items-center gap-2 flex-shrink-0">
                <Leaf size={14} className="text-green-600" />
                <h2 className="text-xs font-semibold text-gray-800">Environmental Impact</h2>
                <span className="text-[10px] text-green-500 ml-auto italic">this assessment cycle</span>
              </div>
              <div className="grid grid-cols-4 gap-4 flex-1 items-center">
                <div className="text-center">
                  <p className="text-4xl font-extrabold text-green-700 leading-none tabular-nums">{kpis!.co2_saved_kg}</p>
                  <p className="text-[11px] font-semibold text-green-600 mt-1.5">kg CO₂ Avoided</p>
                  <p className="text-[10px] text-gray-400">carbon footprint saved</p>
                </div>
                <div className="text-center border-l border-green-200">
                  <p className="text-4xl font-extrabold text-green-700 leading-none tabular-nums">{kpis!.landfill_reduction_kg}</p>
                  <p className="text-[11px] font-semibold text-green-600 mt-1.5">kg Landfill Diverted</p>
                  <p className="text-[10px] text-gray-400">e-waste prevented</p>
                </div>
                <div className="text-center border-l border-green-200">
                  <p className="text-4xl font-extrabold text-green-700 leading-none flex items-center justify-center gap-1">
                    <TreePine size={26} className="text-green-500" />{kpis!.carbon_offset_trees}
                  </p>
                  <p className="text-[11px] font-semibold text-green-600 mt-1.5">Trees Equivalent</p>
                  <p className="text-[10px] text-gray-400">{kpis!.co2_saved_kg} kg CO₂ offset</p>
                </div>
                <div className="text-center border-l border-green-200">
                  <p className="text-4xl font-extrabold text-green-700 leading-none">
                    {kpis!.material_recovery_pct.toFixed(0)}<span className="text-xl font-bold">%</span>
                  </p>
                  <p className="text-[11px] font-semibold text-green-600 mt-1.5">Material Recovery</p>
                  <p className="text-[10px] text-gray-400">rare earth metals</p>
                </div>
              </div>
              {/* Action mix bar */}
              <div className="flex-shrink-0">
                <div className="flex h-1.5 rounded-full overflow-hidden">
                  {(['recycle', 'repair', 'refurbish', 'redeploy'] as const).map(a => {
                    const pct = (kpis!.action_percentages as Record<string, number>)?.[a] ?? 0;
                    return pct > 0 ? <div key={a} style={{ width: `${pct}%`, background: ACTION_COLORS[a] }} title={`${a}: ${pct}%`} /> : null;
                  })}
                </div>
                <div className="flex gap-x-4 justify-center mt-1">
                  {(['recycle', 'repair', 'refurbish', 'redeploy'] as const).map(a => (
                    <span key={a} className="text-[10px] flex items-center gap-1" style={{ color: ACTION_COLORS[a] }}>
                      <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: ACTION_COLORS[a] }} />
                      <span className="capitalize">{a}</span> {(kpis!.action_percentages as Record<string, number>)?.[a] ?? 0}%
                    </span>
                  ))}
                </div>
              </div>
            </div>

          </div>
        </>
      )}
    </div>
  );
}
