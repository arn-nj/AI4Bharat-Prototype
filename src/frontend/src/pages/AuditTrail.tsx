import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { getAuditTrail, getLLMOpinion, type AuditEntryRow } from '../services/api';
import ActionBadge from '../components/ActionBadge';
import { assetTag } from '../utils/assetTag';

const DECISION_STYLE: Record<string, string> = {
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
};

function AuditRow({ e }: { e: AuditEntryRow }) {
  const [expanded, setExpanded] = useState(false);
  const [llmText, setLlmText] = useState<string | null>(e.llm_impact ?? null);
  const [llmLoading, setLlmLoading] = useState(false);
  const hasDetail = !!(e.rationale || llmText || e.llm_pre_decision_json || e.original_action);

  const fetchLLM = async () => {
    setLlmLoading(true);
    try {
      const res = await getLLMOpinion(e.asset_id);
      setLlmText(res.reasoning);
    } catch {
      setLlmText('Unable to fetch AI analysis at this time.');
    } finally {
      setLlmLoading(false);
    }
  };

  return (
    <>
      <tr
        className={`hover:bg-gray-50 ${hasDetail ? 'cursor-pointer' : ''}`}
        onClick={() => hasDetail && setExpanded(p => !p)}
      >
        <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">
          {new Date(e.timestamp).toLocaleString()}
        </td>
        <td className="px-4 py-3">
          {e.device_type && e.department && e.region ? (
            <Link
              to={`/inventory?asset=${e.asset_id}`}
              onClick={ev => ev.stopPropagation()}
              className="font-mono text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:underline"
              title={e.asset_id}
            >
              {assetTag({ asset_id: e.asset_id, device_type: e.device_type, department: e.department, region: e.region })}
            </Link>
          ) : (
            <span className="font-mono text-xs text-gray-400" title={e.asset_id}>{e.asset_id.slice(0, 14)}…</span>
          )}
        </td>
        <td className="px-4 py-3"><ActionBadge action={e.action} size="sm" /></td>
        <td className="px-4 py-3">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${DECISION_STYLE[e.decision] ?? 'bg-gray-100 text-gray-600'}`}>
            {e.decision}
          </span>
        </td>
        <td className="px-4 py-3 text-gray-600 text-sm">{e.actor}</td>
        <td className="px-4 py-3 text-gray-400 text-xs">
          {hasDetail ? (
            <span className={`text-indigo-500 select-none ${expanded ? 'opacity-100' : 'opacity-60'}`}>
              {expanded ? '▲ hide' : '▼ details'}
            </span>
          ) : (
            <span className="text-gray-300">—</span>
          )}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-indigo-50/40 border-b border-indigo-100">
          <td colSpan={6} className="px-5 py-4 space-y-3">
            {e.original_action && (
              <div className="flex items-center gap-2 p-2 bg-amber-50 border border-amber-200 rounded-lg">
                <span className="text-amber-600 text-xs">⚠</span>
                <p className="text-xs font-semibold text-amber-700">
                  Action overridden by manager: <span className="line-through opacity-70">{e.original_action}</span> → <span className="font-bold">{e.action}</span>
                </p>
              </div>
            )}
            {e.llm_pre_decision_json && (() => {
              try {
                const pred = JSON.parse(e.llm_pre_decision_json) as { reasoning?: string; action?: string; risk_level?: string };
                return (
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-violet-400 mb-1">AI Pre-Decision Opinion</p>
                    {pred.action && (
                      <p className="text-xs text-violet-600 font-semibold mb-1">
                        AI recommended: {pred.action}{pred.risk_level ? ` · Risk: ${pred.risk_level}` : ''}
                      </p>
                    )}
                    {pred.reasoning && <p className="text-sm text-gray-700 leading-relaxed">{pred.reasoning}</p>}
                  </div>
                );
              } catch { return null; }
            })()}
            {e.rationale && (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-1">Human Rationale</p>
                <p className="text-sm text-gray-700 leading-relaxed">"{e.rationale}"</p>
              </div>
            )}
            {llmText ? (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-indigo-400 mb-1">AI Impact Analysis</p>
                <p className="text-sm text-gray-700 leading-relaxed">{llmText}</p>
              </div>
            ) : (
              <button
                onClick={e => { e.stopPropagation(); fetchLLM(); }}
                disabled={llmLoading}
                className="text-xs text-indigo-500 underline hover:text-indigo-700 disabled:opacity-50"
              >
                {llmLoading ? 'Fetching AI analysis…' : '✦ Get AI analysis'}
              </button>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

export default function AuditTrail() {
  const [entries, setEntries] = useState<AuditEntryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [searchParams] = useSearchParams();
  const filterAssetId = searchParams.get('asset_id');

  useEffect(() => {
    (async () => {
      try {
        const params: Record<string, string> = {};
        if (filterAssetId) params.asset_id = filterAssetId;
        setEntries(await getAuditTrail(Object.keys(params).length ? params : undefined));
      } finally { setLoading(false); }
    })();
  }, [filterAssetId]);

  const q = search.toLowerCase();
  const filtered = search
    ? entries.filter(e =>
        e.asset_id.toLowerCase().includes(q) ||
        e.action.toLowerCase().includes(q) ||
        e.decision.toLowerCase().includes(q) ||
        e.actor.toLowerCase().includes(q) ||
        (e.device_type ?? '').toLowerCase().includes(q) ||
        (e.department ?? '').toLowerCase().includes(q) ||
        (e.region ?? '').toLowerCase().includes(q) ||
        (e.rationale ?? '').toLowerCase().includes(q)
      )
    : entries;

  return (
    <div className="p-6 space-y-4">
      <div>
        <div className="flex items-center gap-3">
          {filterAssetId && (
            <Link
              to={`/inventory?asset=${filterAssetId}`}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-800 bg-white border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition-colors"
            >
              ← Back to Inventory
            </Link>
          )}
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Audit Trail</h1>
            <p className="text-sm text-gray-500 mt-0.5">Immutable log of all approval decisions · click a row to expand</p>
          </div>
        </div>
        {filterAssetId && (() => {
          const sample = entries.find(e => e.device_type && e.department && e.region);
          const tag = sample
            ? assetTag({ asset_id: filterAssetId, device_type: sample.device_type!, department: sample.department!, region: sample.region! })
            : filterAssetId;
          return (
            <div className="mt-2 flex items-center gap-2 text-xs text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg px-3 py-1.5 w-fit">
              <span>Filtered by asset: <span className="font-mono font-semibold">{tag}</span></span>
              <Link to="/audit" className="ml-1 text-indigo-400 hover:text-indigo-600 underline">Clear filter</Link>
            </div>
          );
        })()}
      </div>

      <div className="flex gap-3">
        <input
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm flex-1 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          placeholder="Search by asset tag, action, decision, actor, rationale…"
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        {search && (
          <button
            onClick={() => setSearch('')}
            className="text-xs px-3 py-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50"
          >
            Clear
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16"><div className="animate-spin h-8 w-8 rounded-full border-b-2 border-green-600" /></div>
        ) : filtered.length === 0 ? (
          <p className="text-center text-gray-400 py-16 text-sm">{search ? 'No matching entries' : 'No decisions recorded yet'}</p>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['Timestamp', 'Asset', 'Action', 'Decision', 'Actor', ''].map((h, i) => (
                  <th key={i} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map(e => <AuditRow key={e.audit_id} e={e} />)}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

