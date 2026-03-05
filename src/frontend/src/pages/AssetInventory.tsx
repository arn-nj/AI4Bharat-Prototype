import { useEffect, useState } from 'react';
import { getAssets, type AssetOut } from '../services/api';
import RiskBadge from '../components/RiskBadge';
import { assetTag } from '../utils/assetTag';

function AssetDetailRow({ a }: { a: AssetOut }) {
  const fmt = (v: number | undefined | null, suffix = '') =>
    v != null ? `${v}${suffix}` : '—';
  const bool = (v: boolean | undefined | null) =>
    v == null ? '—' : v ? 'Yes' : 'No';

  return (
    <tr className="bg-blue-50/30 border-b border-blue-100">
      <td colSpan={8} className="px-5 py-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-x-8 gap-y-2 text-xs">
          {/* Identity */}
          <div className="space-y-1.5">
            <p className="font-bold uppercase tracking-widest text-gray-400 text-[10px]">Identity</p>
            <p><span className="text-gray-400">Asset tag: </span><span className="font-mono font-semibold text-gray-800">{assetTag(a)}</span></p>
            {a.serial_number && <p><span className="text-gray-400">Serial no.: </span><span className="font-mono text-gray-700">{a.serial_number}</span></p>}
            <p><span className="text-gray-400">Asset ID: </span><span className="font-mono text-gray-500 text-[10px]">{a.asset_id}</span></p>
            <p><span className="text-gray-400">Model: </span><span className="text-gray-700">{a.model_name ?? '—'}</span></p>
            <p><span className="text-gray-400">Year: </span><span className="text-gray-700">{a.model_year ?? '—'}</span></p>
            <p><span className="text-gray-400">OS: </span><span className="text-gray-700">{a.os ?? '—'}</span></p>
            <p><span className="text-gray-400">Purchase date: </span><span className="text-gray-700">{a.purchase_date ? a.purchase_date.slice(0, 10) : '—'}</span></p>
          </div>
          {/* Usage */}
          <div className="space-y-1.5">
            <p className="font-bold uppercase tracking-widest text-gray-400 text-[10px]">Usage</p>
            <p><span className="text-gray-400">Type: </span><span className="text-gray-700">{a.usage_type ?? '—'}</span></p>
            <p><span className="text-gray-400">Daily hours: </span><span className="text-gray-700">{fmt(a.daily_usage_hours, 'h')}</span></p>
            <p><span className="text-gray-400">Performance: </span><span className="text-gray-700">{fmt(a.performance_rating, '/10')}</span></p>
            <p><span className="text-gray-400">Office: </span><span className="text-gray-700">{a.region ?? '—'}</span></p>
          </div>
          {/* Hardware health */}
          <div className="space-y-1.5">
            <p className="font-bold uppercase tracking-widest text-gray-400 text-[10px]">Hardware health</p>
            <p><span className="text-gray-400">Battery health: </span><span className="text-gray-700">{fmt(a.battery_health_pct, '%')}</span></p>
            <p><span className="text-gray-400">Battery cycles: </span><span className="text-gray-700">{fmt(a.battery_cycles)}</span></p>
            <p><span className="text-gray-400">SMART failures: </span><span className="text-gray-700">{fmt(a.smart_sectors_reallocated)}</span></p>
            <p><span className="text-gray-400">Thermal events: </span><span className="text-gray-700">{fmt(a.thermal_events_count)}</span></p>
            <p><span className="text-gray-400">Overheating: </span><span className={`font-medium ${a.overheating_issues ? 'text-red-600' : 'text-gray-700'}`}>{bool(a.overheating_issues)}</span></p>
          </div>
          {/* Incidents */}
          <div className="space-y-1.5">
            <p className="font-bold uppercase tracking-widest text-gray-400 text-[10px]">Incidents (90d)</p>
            <p><span className="text-gray-400">Total: </span><span className="text-gray-700">{fmt(a.total_incidents)}</span></p>
            <p><span className="text-gray-400">Critical: </span><span className={`font-medium ${(a.critical_incidents ?? 0) > 0 ? 'text-red-600' : 'text-gray-700'}`}>{fmt(a.critical_incidents)}</span></p>
            <p><span className="text-gray-400">High: </span><span className="text-gray-700">{fmt(a.high_incidents)}</span></p>
            <p><span className="text-gray-400">Medium: </span><span className="text-gray-700">{fmt(a.medium_incidents)}</span></p>
            <p><span className="text-gray-400">Low: </span><span className="text-gray-700">{fmt(a.low_incidents)}</span></p>
            <p><span className="text-gray-400">Avg resolution: </span><span className="text-gray-700">{fmt(a.avg_resolution_time_hours, 'h')}</span></p>
          </div>
        </div>
      </td>
    </tr>
  );
}

export default function AssetInventory() {
  const [assets, setAssets] = useState<AssetOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dept, setDept] = useState('');
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = { page: String(page), page_size: '20' };
      if (dept) params.department = dept;
      const data = await getAssets(params);
      setAssets(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [page, dept]);

  const filtered = search
    ? assets.filter(a =>
        a.asset_id.toLowerCase().includes(search.toLowerCase()) ||
        a.device_type.toLowerCase().includes(search.toLowerCase()) ||
        a.department.toLowerCase().includes(search.toLowerCase())
      )
    : assets;

  const STATE_BADGE: Record<string, string> = {
    active:           'bg-green-100 text-green-700',
    review_pending:   'bg-yellow-100 text-yellow-700',
    workflow_in_progress: 'bg-blue-100 text-blue-700',
    closed:           'bg-gray-100 text-gray-600',
  };

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Asset Inventory</h1>
        <p className="text-sm text-gray-500 mt-0.5">All managed IT assets</p>
      </div>

      <div className="flex gap-3">
        <input
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm flex-1 focus:outline-none focus:ring-2 focus:ring-green-500"
          placeholder="Search by ID, type or department…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <input
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-green-500"
          placeholder="Department filter"
          value={dept}
          onChange={e => { setDept(e.target.value); setPage(1); }}
        />
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin h-8 w-8 rounded-full border-b-2 border-green-600" />
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-center text-gray-400 py-16 text-sm">No assets found</p>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['Asset ID', 'Type', 'Brand', 'Department', 'Region', 'Age', 'Completeness', 'State'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map(a => (
                <>
                  <tr
                    key={a.asset_id}
                    className="hover:bg-gray-50 transition-colors cursor-pointer"
                    onClick={() => setExpandedId(id => id === a.asset_id ? null : a.asset_id)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-gray-600">{a.asset_id.slice(0, 14)}…</td>
                    <td className="px-4 py-3">{a.device_type}</td>
                    <td className="px-4 py-3 text-gray-500">{a.brand ?? '—'}</td>
                    <td className="px-4 py-3">{a.department}</td>
                    <td className="px-4 py-3 text-gray-500">{a.region}</td>
                    <td className="px-4 py-3">{a.age_months}m</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 bg-gray-100 rounded-full">
                          <div className="h-full bg-green-500 rounded-full" style={{ width: `${Math.round(a.data_completeness * 100)}%` }} />
                        </div>
                        <span className="text-xs text-gray-400">{Math.round(a.data_completeness * 100)}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATE_BADGE[a.current_state] ?? 'bg-gray-100 text-gray-600'}`}>
                        {a.current_state.replace(/_/g, ' ')}
                      </span>
                    </td>
                  </tr>
                  {expandedId === a.asset_id && <AssetDetailRow a={a} />}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center text-sm text-gray-500">
        <span>{filtered.length} records shown</span>
        <div className="flex gap-2">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="px-3 py-1 border rounded-lg hover:bg-gray-50 disabled:opacity-40">Prev</button>
          <span className="px-3 py-1">Page {page}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={assets.length < 20}
            className="px-3 py-1 border rounded-lg hover:bg-gray-50 disabled:opacity-40">Next</button>
        </div>
      </div>
    </div>
  );
}
