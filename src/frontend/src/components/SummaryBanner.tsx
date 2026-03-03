import type { AnalysisResult, Scenario } from '../types'
import { ActionBadge } from './Badge'

export function SummaryBanner({ result, scenario }: { result: AnalysisResult; scenario: Scenario }) {
  const match = result.final_action === scenario._expected_action

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-gray-800 mb-3">Analysis Result</h2>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <p className="text-xs text-gray-500 font-medium mb-1">Final Action</p>
          <ActionBadge action={result.final_action} />
        </div>
        <div>
          <p className="text-xs text-gray-500 font-medium mb-1">Confidence Score</p>
          <p className="text-2xl font-bold text-gray-900">{result.confidence_score.toFixed(3)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 font-medium mb-1">Expected Action</p>
          <p className="text-sm font-mono text-gray-700">{scenario._expected_action}</p>
          <p className={`text-xs mt-1 font-semibold ${match ? 'text-green-600' : 'text-red-600'}`}>
            {match ? '✓ Match' : '✗ Mismatch — review scenario'}
          </p>
        </div>
      </div>
    </div>
  )
}
