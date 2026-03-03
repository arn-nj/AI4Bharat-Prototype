import type { AnalysisResult, Scenario } from './types'

// VITE_BACKEND_URL is injected at build time (e.g. https://pacyjst474.execute-api.us-east-1.amazonaws.com/dev)
// Falls back to empty string so relative URLs work with the Vite dev proxy.
const BASE = import.meta.env.VITE_BACKEND_URL ?? ''

export async function checkHealth(): Promise<boolean> {
  try {
    const resp = await fetch(`${BASE}/health`, {
      signal: AbortSignal.timeout(4000),
    })
    return resp.ok
  } catch {
    return false
  }
}

/** Strip internal _* keys before sending to the API. */
export function buildPayload(scenario: Scenario): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(scenario).filter(([k]) => !k.startsWith('_')),
  )
}

export async function analyseDevice(payload: Record<string, unknown>): Promise<AnalysisResult> {
  const resp = await fetch(`${BASE}/analyse_device`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(90_000),
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`HTTP ${resp.status}: ${text}`)
  }
  return resp.json() as Promise<AnalysisResult>
}
