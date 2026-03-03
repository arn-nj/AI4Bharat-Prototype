import type { FinalAction, RiskLabel } from '../types'

const ACTION_CLS: Record<FinalAction, string> = {
  RECYCLE:   'bg-red-700 text-white',
  REPAIR:    'bg-orange-600 text-white',
  REFURBISH: 'bg-yellow-500 text-white',
  RESALE:    'bg-green-700 text-white',
  REDEPLOY:  'bg-blue-700 text-white',
}

const RISK_CLS: Record<RiskLabel, string> = {
  high:   'bg-red-600 text-white',
  medium: 'bg-yellow-500 text-white',
  low:    'bg-green-600 text-white',
}

export function ActionBadge({ action }: { action: FinalAction }) {
  return (
    <span className={`inline-block px-3 py-1 rounded text-sm font-bold ${ACTION_CLS[action] ?? 'bg-gray-500 text-white'}`}>
      {action}
    </span>
  )
}

export function RiskBadge({ label }: { label: RiskLabel }) {
  return (
    <span className={`inline-block px-3 py-1 rounded text-sm font-semibold ${RISK_CLS[label] ?? 'bg-gray-500 text-white'}`}>
      {label.toUpperCase()}
    </span>
  )
}
