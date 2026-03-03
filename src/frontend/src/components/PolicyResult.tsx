import type { PolicyResult as PolicyResultType } from '../types'
import { ActionBadge, RiskBadge } from './Badge'

export function PolicyResult({ policy }: { policy: PolicyResultType }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500 font-medium mb-2">Classification</p>
          <RiskBadge label={policy.classification} />
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500 font-medium mb-2">Recommended Action</p>
          <ActionBadge action={policy.recommended_action} />
        </div>
      </div>

      <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900 space-y-1">
        <p className="font-semibold mb-2">Policy Rules Applied</p>
        <ul className="space-y-1 text-xs list-disc list-inside">
          <li><code>age_in_months</code> ≥ 42 AND ≥ 5 incidents → aged high-incident flag</li>
          <li><code>thermal_events_count</code> ≥ 10 → High risk rule</li>
          <li><code>smart_sectors_reallocated</code> ≥ 50 → High risk rule</li>
          <li><code>overheating_issues</code> + risk score → qualifies REPAIR action</li>
          <li>risk_score ≥ 0.80 AND age ≥ 42 months → <strong>RECYCLE</strong></li>
          <li>risk_score ≥ 0.70 AND repairable → <strong>REPAIR</strong></li>
          <li>risk_score ≥ 0.50 → <strong>REFURBISH</strong></li>
          <li>risk_score &lt; 0.30 → <strong>REDEPLOY</strong></li>
          <li>otherwise → <strong>RESALE</strong></li>
        </ul>
      </div>

      {policy.supporting_signals.length > 0 && (
        <div>
          <p className="text-sm font-semibold text-gray-700 mb-2">Supporting Signals</p>
          <ul className="space-y-1">
            {policy.supporting_signals.map((sig, i) => (
              <li key={i} className="text-sm text-gray-600 flex gap-2">
                <span className="text-gray-400">•</span>
                <span>{sig}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {policy.policy_version && (
        <p className="text-xs text-gray-400">Policy version: {policy.policy_version}</p>
      )}
    </div>
  )
}
