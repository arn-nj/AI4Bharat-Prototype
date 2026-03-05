import { useEffect, useState } from 'react';
import { getApprovalQueue, decideApproval, approveAll, getLLMOpinion, type ApprovalQueueItem, type AuditEntry, type LLMPrediction } from '../services/api';
import ActionBadge from '../components/ActionBadge';
import ConfidenceBar from '../components/ConfidenceBar';
import RiskBadge from '../components/RiskBadge';
import { assetTag } from '../utils/assetTag';

const RISK_COLORS: Record<string, string> = {
  high:   'text-red-700 bg-red-50 border-red-200',
  medium: 'text-orange-700 bg-orange-50 border-orange-200',
  low:    'text-green-700 bg-green-50 border-green-200',
};

const ACTIONS = ['recycle', 'repair', 'refurbish', 'redeploy', 'resale'];

export default function ApprovalQueue() {
  const [queue, setQueue] = useState<ApprovalQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ApprovalQueueItem | null>(null);
  const [rationale, setRationale] = useState('');
  const [actor, setActor]   = useState('admin');
  const [submitting, setSubmitting] = useState(false);
  const [lastDecision, setLastDecision] = useState<AuditEntry | null>(null);
  const [bulkApproving, setBulkApproving] = useState(false);
  const [llmOpinion, setLlmOpinion] = useState<LLMPrediction | null>(null);
  const [loadingOpinion, setLoadingOpinion] = useState(false);
  const [llmFailed, setLlmFailed] = useState(false);
  const [overrideAction, setOverrideAction] = useState<string>('');

  const load = async () => {
    setLoading(true);
    try { setQueue(await getApprovalQueue()); } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  // Auto-fetch AI opinion whenever a new item is selected
  useEffect(() => {
    if (!selected) return;
    setLlmOpinion(null);
    setLlmFailed(false);
    setLoadingOpinion(true);
    getLLMOpinion(selected.asset_id)
      .then(pred => setLlmOpinion(pred))
      .catch(() => setLlmFailed(true))
      .finally(() => setLoadingOpinion(false));
  }, [selected?.recommendation_id]);

  const selectItem = (item: ApprovalQueueItem) => {
    setSelected(item);
    setOverrideAction('');
  };

  const decide = async (decision: 'approved' | 'rejected') => {
    if (!selected || !rationale.trim()) return;
    setSubmitting(true);
    try {
      const payload: Parameters<typeof decideApproval>[1] = { decision, rationale, actor };
      if (decision === 'approved' && overrideAction && overrideAction !== selected.action) {
        payload.override_action = overrideAction;
      }
      const result = await decideApproval(selected.recommendation_id, payload);
      setLastDecision(result);
      setSelected(null);
      setRationale('');
      setLlmOpinion(null);
      setOverrideAction('');
      await load();
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproveAll = async () => {
    if (!window.confirm(`Approve all ${queue.length} pending item${queue.length !== 1 ? 's' : ''}? This cannot be undone.`)) return;
    setBulkApproving(true);
    try {
      await approveAll({ rationale: 'Bulk approved by manager', actor });
      setSelected(null);
      setLlmOpinion(null);
      setOverrideAction('');
      await load();
    } finally {
      setBulkApproving(false);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Approval Queue</h1>
          <p className="text-sm text-gray-500 mt-0.5">{queue.length} recommendation{queue.length !== 1 ? 's' : ''} pending review</p>
        </div>
        {queue.length > 0 && (
          <button
            onClick={handleApproveAll}
            disabled={bulkApproving}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded-lg transition-colors disabled:opacity-50"
          >
            {bulkApproving ? (
              <><span className="inline-block w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> Approving all…</>
            ) : (
              <>✓ Approve All ({queue.length})</>
            )}
          </button>
        )}
      </div>

      {/* Decision result banner */}
      {lastDecision && (
        <div className={`rounded-xl border p-4 flex items-start gap-3 ${lastDecision.decision === 'approved' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
          <span className={`text-lg flex-shrink-0 mt-0.5 ${lastDecision.decision === 'approved' ? 'text-green-600' : 'text-red-500'}`}>
            {lastDecision.decision === 'approved' ? '✓' : '✗'}
          </span>
          <div className="flex-1 min-w-0">
            <p className={`text-sm font-semibold ${lastDecision.decision === 'approved' ? 'text-green-800' : 'text-red-700'}`}>
              {lastDecision.decision === 'approved' ? 'Approved' : 'Rejected'} · {lastDecision.action}
            </p>
            {lastDecision.rationale && (
              <p className="text-xs text-gray-600 mt-1 italic">“{lastDecision.rationale}”</p>
            )}
            {lastDecision.llm_impact ? (
              <p className="text-sm text-gray-700 mt-1.5 leading-relaxed">{lastDecision.llm_impact}</p>
            ) : (
              <p className="text-xs text-gray-500 mt-0.5">Decision recorded by {lastDecision.actor}</p>
            )}
          </div>
          <button onClick={() => setLastDecision(null)} className="text-gray-400 hover:text-gray-600 text-lg leading-none flex-shrink-0" aria-label="Dismiss">×</button>
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
                onClick={() => selectItem(item)}
                className={`w-full text-left bg-white rounded-xl shadow-sm border p-4 transition-all hover:shadow-md ${
                  selected?.recommendation_id === item.recommendation_id ? 'border-green-400 ring-2 ring-green-200' : 'border-gray-100'
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="font-medium text-sm">{item.device_type} · {item.department}</p>
                    <p className="text-xs text-gray-400">{assetTag(item)} · {item.region} · {item.age_months}m old</p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <ActionBadge action={item.action} size="sm" />
                    {item.risk_level && <RiskBadge level={item.risk_level} />}
                  </div>
                </div>
                <ConfidenceBar score={item.confidence_score} />
                {item.risk_score != null && (
                  <p className="text-[11px] text-gray-400 mt-1">Risk score: <span className="font-medium text-gray-600">{(item.risk_score * 100).toFixed(0)}%</span>{item.confidence_band && <span> · {item.confidence_band} confidence</span>}</p>
                )}
                <p className="text-xs text-gray-500 mt-2 line-clamp-2">{item.rationale}</p>
              </button>
            ))}
          </div>

          {/* Decision panel */}
          {selected && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
              <h2 className="font-semibold text-gray-800">Make Decision</h2>

              {/* ML Risk Assessment */}
              {selected.risk_level && (
                <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1.5">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 mb-1">ML Risk Assessment</p>
                  <div className="flex items-center gap-2">
                    <RiskBadge level={selected.risk_level} />
                    {selected.risk_score != null && (
                      <span className="text-xs text-gray-500">Score: <span className="font-medium text-gray-700">{(selected.risk_score * 100).toFixed(0)}%</span></span>
                    )}
                    {selected.confidence_band && (
                      <span className="text-xs text-gray-500">· {selected.confidence_band} confidence</span>
                    )}
                  </div>
                </div>
              )}

              <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
                <p><span className="text-gray-500">Asset:</span> <span className="font-mono font-medium text-gray-800">{assetTag(selected)}</span></p>
                <p><span className="text-gray-500">Current recommendation:</span> <span className="capitalize font-medium">{selected.action}</span></p>
              </div>
              <p className="text-sm text-gray-600">{selected.rationale}</p>

              {/* AI Opinion — auto-loads on selection */}
              {loadingOpinion ? (
                <div className="rounded-lg border border-indigo-100 bg-indigo-50/40 p-3 flex items-center gap-2 text-xs text-indigo-500">
                  <span className="inline-block w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                  Fetching AI opinion…
                </div>
              ) : llmOpinion ? (
                <div className={`rounded-lg border p-3 text-xs space-y-1 ${
                  RISK_COLORS[llmOpinion.risk_level] ?? 'bg-gray-50 border-gray-200 text-gray-700'
                }`}>
                  <p className="font-semibold text-[11px] uppercase tracking-wide opacity-60 mb-1">AI Opinion (Qwen3)</p>
                  <p>Risk: <span className="font-semibold capitalize">{llmOpinion.risk_level}</span> · Action: <span className="font-semibold capitalize">{llmOpinion.action}</span></p>
                  <p className="italic opacity-80 leading-relaxed">{llmOpinion.reasoning}</p>
                </div>
              ) : llmFailed ? (
                <button
                  onClick={() => {
                    setLlmFailed(false);
                    setLoadingOpinion(true);
                    getLLMOpinion(selected.asset_id)
                      .then(pred => setLlmOpinion(pred))
                      .catch(() => setLlmFailed(true))
                      .finally(() => setLoadingOpinion(false));
                  }}
                  className="w-full border border-indigo-200 text-indigo-600 hover:bg-indigo-50 text-sm font-medium py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  ✦ Retry AI Opinion
                </button>
              ) : null}

              {/* Action override */}
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Override action
                  <span className="ml-1 font-normal text-gray-400">(optional — leave blank to keep recommendation)</span>
                </label>
                <select
                  value={overrideAction}
                  onChange={e => setOverrideAction(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500 bg-white"
                >
                  <option value="">— Keep recommended: {selected.action} —</option>
                  {ACTIONS.filter(a => a !== selected.action).map(a => (
                    <option key={a} value={a} className="capitalize">{a.charAt(0).toUpperCase() + a.slice(1)}</option>
                  ))}
                </select>
                {overrideAction && (
                  <p className="text-[11px] text-amber-600 mt-1">
                    ⚠ Will approve as <span className="font-semibold capitalize">{overrideAction}</span> instead of <span className="font-semibold capitalize">{selected.action}</span>
                  </p>
                )}
              </div>

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
