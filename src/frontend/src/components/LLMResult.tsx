import type { IstmTask, LLMResult as LLMResultType } from '../types'

function parseItsm(raw: IstmTask | string | null): IstmTask | null {
  if (!raw) return null
  if (typeof raw === 'string') {
    try { return JSON.parse(raw) as IstmTask } catch { return null }
  }
  return raw
}

export function LLMResult({ llm }: { llm: LLMResultType }) {
  const itsm = parseItsm(llm.itsm_task)

  return (
    <div className="space-y-4">
      {!llm.llm_available && (
        <div className="rounded bg-yellow-50 border border-yellow-200 px-4 py-2 text-sm text-yellow-800">
          Live LLM was unavailable. A deterministic fallback template was used.
        </div>
      )}

      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <p className="text-sm font-semibold text-gray-700 mb-2">Recommendation Explanation</p>
        <blockquote className="border-l-4 border-blue-400 pl-4 text-sm text-gray-700 italic">
          {llm.explanation}
        </blockquote>
      </div>

      {itsm && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
          <p className="text-sm font-semibold text-gray-700">ITSM Task</p>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-xs text-gray-500 font-medium">Title</p>
              <p className="text-gray-900">{itsm.title}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 font-medium">Priority</p>
              <p className="text-gray-900">{itsm.priority}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 font-medium">Assigned Team</p>
              <p className="text-gray-900">{itsm.assigned_team}</p>
            </div>
          </div>
          <div>
            <p className="text-xs text-gray-500 font-medium mb-1">Description</p>
            <p className="text-sm text-gray-800">{itsm.description}</p>
          </div>
          {itsm.checklist?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 font-medium mb-1">Checklist</p>
              <ul className="space-y-1">
                {itsm.checklist.map((item, i) => (
                  <li key={i} className="text-sm text-gray-700 flex gap-2">
                    <span className="text-gray-400">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
