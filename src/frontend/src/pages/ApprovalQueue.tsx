import { useEffect, useState } from 'react';
import { getApprovalQueue, decideApproval, type ApprovalQueueItem, type AuditEntry } from '../services/api';
import ActionBadge from '../components/ActionBadge';
import ConfidenceBar from '../components/ConfidenceBar';

export default function ApprovalQueue() {
  const [queue, setQueue] = useState<ApprovalQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ApprovalQueueItem | null>(null);
  const [rationale, setRationale] = useState('');
  const [actor, setActor]   = useState('admin');
  const [submitting, setSubmitting] = useState(false);
  const [lastDecision, setLastDecision] = useState<AuditEntry | null>(null);

  const load = async () => {
    setLoading(true);
    try { setQueue(await getApprovalQueue()); } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const decide = async (decision: 'approved' | 'rejected') => {
    if (!selected || !rationale.trim()) return;
    setSubmitting(true);
    try {
      const result = await decideApproval(selected.recommendation_id, { decision, rationale, actor });
      setLastDecision(result);
      setSelected(null);
      setRationale('');
      await load();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Approval Queue</h1>
        <p className="text-sm text-gray-500 mt-0.5">{queue.length} recommendation{queue.length !== 1 ? 's' : ''} pending review</p>
      </div>

      {/* Decision result banner */}
      {lastDecision && (
        <div className={`rounded-xl border p-4 flex items-start gap-3 ${lastDecision.decision === 'approved' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
          <span className={`text-lg flex-shrink-0 mt-0.5 ${lastDecision.decision === 'approved' ? 'text-green-600' : 'text-red-500'}`}>
            {lastDecision.decision === 'approved' ? '✓' : '✗'}
          </span>
          <div className="flex-1 min-w-0">
            <p className={`text-sm font-semibold ${lastDecision.decision === 'approved' ? 'text-green-800' : 'text-red-700'}`}>
              {lastDecision.decision === 'approved' ? 'Approved' : 'Rejected'} · {lastDecision.asset_id} · {lastDecision.action}
            </p>
            {lastDecision.llm_impact ? (
              <p className="text-sm text-gray-700 mt-1 leading-relaxed">{lastDecision.llm_impact}</p>
            ) : (
              <p className="text-xs text-gray-500 mt-0.5">Decision recorded by {lastDecision.actor}</p>
            )}
          </div>
          <button
            onClick={() => setLastDecision(null)}
            className="text-gray-400 hover:text-gray-600 text-lg leading-none flex-shrink-0"
            aria-label="Dismiss"
          >×</button>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><div className="animate-spin h-8 w-8 rounded-full border-b-2 border-green-600" /></div>
      ) : queue.length === 0 ? (
        <div className="bg-white rounded-xl border-2 border-dashed border-gray-200 p-12 text-center text-gray-400">
          <p className="text-lg font-medium">Queue is empty</p>
          <p className="text-sm mt-1">All recommendations have been processed</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {/* Queue list */}
          <div className="space-y-2">
            {queue.map(item => (
              <button
                key={item.recommendation_id}
                onClick={() => setSelected(item)}
                className={`w-full text-left bg-white rounded-xl shadow-sm border p-4 transition-all hover:shadow-md ${selected?.recommendation_id === item.recommendation_id ? 'border-green-400 ring-2 ring-green-200' : 'border-gray-100'}`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="font-medium text-sm">{item.device_type} · {item.department}</p>
                    <p className="text-xs text-gray-400">{item.region} · {item.age_months}m old</p>
                  </div>
                  <ActionBadge action={item.action} size="sm" />
                </div>
                <ConfidenceBar score={item.confidence_score} />
                <p className="text-xs text-gray-500 mt-2 line-clamp-2">{item.rationale}</p>
              </button>
            ))}
          </div>

          {/* Decision panel */}
          {selected && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
              <h2 className="font-semibold text-gray-800">Make Decision</h2>
              <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
                <p><span className="text-gray-500">Asset:</span> {selected.asset_id}</p>
                <p><span className="text-gray-500">Action:</span> <span className="capitalize font-medium">{selected.action}</span></p>
                <p><span className="text-gray-500">Policy:</span> {selected.policy_version}</p>
              </div>
              <p className="text-sm text-gray-600">{selected.rationale}</p>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Your Rationale *</label>
                <textarea
                  rows={3}
                  value={rationale}
                  onChange={e => setRationale(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Explain your decision…"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Actor</label>
                <input value={actor} onChange={e => setActor(e.target.value)} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500" />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => decide('approved')}
                  disabled={submitting || !rationale.trim()}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-2 rounded-lg text-sm transition-colors disabled:opacity-50"
                >
                  ✓ Approve
                </button>
                <button
                  onClick={() => decide('rejected')}
                  disabled={submitting || !rationale.trim()}
                  className="flex-1 bg-red-500 hover:bg-red-600 text-white font-semibold py-2 rounded-lg text-sm transition-colors disabled:opacity-50"
                >
                  ✗ Reject
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
