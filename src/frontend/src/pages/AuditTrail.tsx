import { useEffect, useState } from 'react';
import { getAuditTrail, type AuditEntryRow } from '../services/api';
import ActionBadge from '../components/ActionBadge';

export default function AuditTrail() {
  const [entries, setEntries] = useState<AuditEntryRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try { setEntries(await getAuditTrail()); } finally { setLoading(false); }
    })();
  }, []);

  const DECISION_STYLE: Record<string, string> = {
    approved: 'bg-green-100 text-green-700',
    rejected: 'bg-red-100 text-red-700',
  };

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Trail</h1>
        <p className="text-sm text-gray-500 mt-0.5">Immutable log of all approval decisions</p>
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
                {['Timestamp', 'Asset', 'Action', 'Decision', 'Actor', 'Rationale'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {entries.map(e => (
                <tr key={e.audit_id} className="hover:bg-gray-50">
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
                  <td className="px-4 py-3 text-gray-600">{e.actor}</td>
                  <td className="px-4 py-3 text-gray-500 max-w-xs truncate" title={e.rationale}>{e.rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
