import { useEffect, useState } from 'react';
import { getAuditTrail, getLLMOpinion, type AuditEntryRow } from '../services/api';
import ActionBadge from '../components/ActionBadge';

const DECISION_STYLE: Record<string, string> = {
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
};

function AuditRow({ e }: { e: AuditEntryRow }) {
  const [expanded, setExpanded] = useState(false);
  const [llmText, setLlmText] = useState<string | null>(e.llm_impact ?? null);
  const [llmLoading, setLlmLoading] = useState(false);
  const hasDetail = !!(e.rationale || llmText);

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
        <td className="px-4 py-3 font-mono text-xs text-gray-600">{e.asset_id.slice(0, 14)}…</td>
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

  useEffect(() => {
    (async () => {
      try { setEntries(await getAuditTrail()); } finally { setLoading(false); }
    })();
  }, []);

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Trail</h1>
        <p className="text-sm text-gray-500 mt-0.5">Immutable log of all approval decisions · click a row to expand</p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16"><div className="animate-spin h-8 w-8 rounded-full border-b-2 border-green-600" /></div>
        ) : entries.length === 0 ? (
          <p className="text-center text-gray-400 py-16 text-sm">No decisions recorded yet</p>
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
              {entries.map(e => <AuditRow key={e.audit_id} e={e} />)}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

