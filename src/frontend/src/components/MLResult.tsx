import type { MLResult as MLResultType } from '../types'
import { RiskBadge } from './Badge'

export function MLResult({ ml }: { ml: MLResultType }) {
  if (!ml.ml_available) {
    return (
      <div className="rounded bg-yellow-50 border border-yellow-200 px-4 py-3 text-sm text-yellow-800">
        ML model was skipped because <code>data_completeness &lt; 0.6</code>. The policy engine ran independently.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500 font-medium mb-2">Risk Label</p>
          <RiskBadge label={ml.risk_label} />
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500 font-medium mb-2">Risk Score</p>
          <p className="text-2xl font-bold text-gray-900">{ml.risk_score.toFixed(3)}</p>
        </div>
      </div>
      {ml.model_version && (
        <p className="text-xs text-gray-400">Model version (trained at): {ml.model_version}</p>
      )}
    </div>
  )
}
