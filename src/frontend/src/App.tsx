import { useEffect, useState } from 'react'
import { analyseDevice, buildPayload, checkHealth } from './api'
import { DeviceTable } from './components/DeviceTable'
import { LLMResult } from './components/LLMResult'
import { MLResult } from './components/MLResult'
import { PolicyResult } from './components/PolicyResult'
import { SummaryBanner } from './components/SummaryBanner'
import { SCENARIOS } from './scenarios'
import type { AnalysisResult } from './types'

type Tab = 'ml' | 'policy' | 'llm'

export default function App() {
  const [backendOk, setBackendOk] = useState<boolean | null>(null)
  const [scenarioIdx, setScenarioIdx] = useState(0)
  const [analysing, setAnalysing] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('ml')

  const scenario = SCENARIOS[scenarioIdx]

  useEffect(() => {
    checkHealth().then(setBackendOk)
  }, [])

  async function handleAnalyse() {
    setAnalysing(true)
    setResult(null)
    setError(null)
    try {
      const data = await analyseDevice(buildPayload(scenario))
      setResult(data)
      setActiveTab('ml')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setAnalysing(false)
    }
  }

  function handleScenarioChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setScenarioIdx(Number(e.target.value))
    setResult(null)
    setError(null)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">E-Waste Asset Lifecycle Optimizer</h1>
        <p className="text-sm text-gray-500 mt-1">
          Select a preset device scenario, then run the full ML + Policy + LLM analysis pipeline.
        </p>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">
        {/* Backend status */}
        <div>
          {backendOk === null && (
            <div className="rounded bg-gray-100 border border-gray-200 px-4 py-2 text-sm text-gray-500">
              Checking backend…
            </div>
          )}
          {backendOk === true && (
            <div className="rounded bg-green-50 border border-green-200 px-4 py-2 text-sm text-green-800">
              ✓ Backend reachable
            </div>
          )}
          {backendOk === false && (
            <div className="rounded bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-800">
              ✗ Backend not reachable. Start the FastAPI backend before running analysis.
            </div>
          )}
        </div>

        {/* Scenario selector */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <label className="block text-sm font-medium text-gray-700 mb-2" htmlFor="scenario-select">
            Select a preset scenario
          </label>
          <select
            id="scenario-select"
            className="w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={scenarioIdx}
            onChange={handleScenarioChange}
          >
            {SCENARIOS.map((s, i) => (
              <option key={i} value={i}>
                {i + 1}. {s._name}
              </option>
            ))}
          </select>
        </div>

        {/* Device characteristics */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <DeviceTable scenario={scenario} />
        </div>

        {/* Analyse button */}
        <div className="flex items-center gap-4">
          <button
            onClick={handleAnalyse}
            disabled={!backendOk || analysing}
            className="rounded bg-blue-700 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {analysing ? 'Analysing…' : 'Start Analysis'}
          </button>
          {!backendOk && backendOk !== null && (
            <p className="text-sm text-gray-500">Start the FastAPI backend to enable analysis.</p>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="rounded bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-800">
            Analysis failed: {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-4">
            <SummaryBanner result={result} scenario={scenario} />

            {/* Tabs */}
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <div className="flex border-b border-gray-200">
                {(['ml', 'policy', 'llm'] as Tab[]).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`px-5 py-3 text-sm font-medium transition-colors ${
                      activeTab === tab
                        ? 'border-b-2 border-blue-600 text-blue-700 bg-blue-50'
                        : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {tab === 'ml' ? 'ML Model' : tab === 'policy' ? 'Policy Engine' : 'LLM Engine'}
                  </button>
                ))}
              </div>
              <div className="p-4">
                {activeTab === 'ml'     && <MLResult     ml={result.ml_result} />}
                {activeTab === 'policy' && <PolicyResult policy={result.policy_result} />}
                {activeTab === 'llm'    && <LLMResult    llm={result.llm_result} />}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
