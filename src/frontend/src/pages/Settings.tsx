import { useState } from 'react';
import { generateDemo, resetDemo, suggestPolicy, analyzeComplianceDoc, type ComplianceDocResult } from '../services/api';

export default function Settings() {
  const [count, setCount]   = useState(10);
  const [dept, setDept]     = useState('');
  const [region, setRegion] = useState('');
  const [autoAssess, setAutoAssess] = useState(true);
  const [genLoading, setGenLoading] = useState(false);
  const [genResult, setGenResult]   = useState<string | null>(null);
  const [resetLoading, setResetLoading] = useState(false);

  const [policy, setPolicy] = useState({
    age_threshold_months: 42,
    ticket_threshold: 5,
    thermal_threshold: 10,
    smart_sector_threshold: 50,
  });
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [suggestLoading, setSuggestLoading] = useState(false);

  const [docType, setDocType] = useState('certificate');
  const [docRegion, setDocRegion] = useState('India');
  const [docAssetId, setDocAssetId] = useState('');
  const [docContent, setDocContent] = useState('');
  const [docResult, setDocResult] = useState<ComplianceDocResult | null>(null);
  const [docLoading, setDocLoading] = useState(false);

  const handleGenerate = async () => {
    setGenLoading(true);
    setGenResult(null);
    try {
      const r = await generateDemo({ count, department: dept || undefined, region: region || undefined, auto_assess: autoAssess });
      setGenResult(r.message);
    } catch (e: unknown) {
      setGenResult(`Error: ${e instanceof Error ? e.message : 'Failed'}`);
    } finally {
      setGenLoading(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Are you sure? This will delete ALL data.')) return;
    setResetLoading(true);
    try {
      const r = await resetDemo();
      setGenResult(r.message);
    } finally {
      setResetLoading(false);
    }
  };

  const handleSuggest = async () => {
    setSuggestLoading(true);
    try {
      const r = await suggestPolicy(policy);
      setSuggestion(r.suggestion);
    } finally {
      setSuggestLoading(false);
    }
  };

  const handleAnalyzeDoc = async () => {
    if (!docContent.trim()) return;
    setDocLoading(true);
    setDocResult(null);
    try {
      const r = await analyzeComplianceDoc({
        document_type: docType,
        region: docRegion,
        asset_id: docAssetId || 'N/A',
        file_content: docContent,
      });
      setDocResult(r);
    } finally {
      setDocLoading(false);
    }
  };

  const inputClass = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500';
  const labelClass = 'block text-xs font-medium text-gray-600 mb-1';

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-0.5">Demo data management &amp; policy configuration</p>
      </div>

      {/* Demo data generator */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">Demo Data Generator</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelClass}>Number of devices</label>
            <input type="number" className={inputClass} value={count} min={1} max={50} onChange={e => setCount(Number(e.target.value))} />
          </div>
          <div>
            <label className={labelClass}>Department (optional)</label>
            <input className={inputClass} value={dept} onChange={e => setDept(e.target.value)} placeholder="e.g. IT" />
          </div>
          <div>
            <label className={labelClass}>Region (optional)</label>
            <input className={inputClass} value={region} onChange={e => setRegion(e.target.value)} placeholder="e.g. North" />
          </div>
          <div className="flex items-center gap-2 pt-5">
            <input type="checkbox" id="auto" checked={autoAssess} onChange={e => setAutoAssess(e.target.checked)} className="rounded" />
            <label htmlFor="auto" className="text-sm text-gray-600">Auto-assess generated devices</label>
          </div>
        </div>
        <div className="flex gap-3">
          <button onClick={handleGenerate} disabled={genLoading}
            className="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-2 rounded-lg text-sm transition-colors disabled:opacity-50">
            {genLoading ? 'Generating…' : 'Generate Fleet'}
          </button>
          <button onClick={handleReset} disabled={resetLoading}
            className="px-4 py-2 border border-red-200 text-red-600 hover:bg-red-50 rounded-lg text-sm font-medium transition-colors disabled:opacity-50">
            {resetLoading ? 'Resetting…' : 'Reset All Data'}
          </button>
        </div>
        {genResult && (
          <p className={`text-sm rounded-lg px-3 py-2 ${genResult.startsWith('Error') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-700'}`}>
            {genResult}
          </p>
        )}
      </section>

      {/* Policy thresholds */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
        <h2 className="font-semibold text-gray-800">Policy Thresholds</h2>
        <p className="text-xs text-gray-500">Adjust thresholds and ask the AI assistant for tuning recommendations.</p>
        <div className="grid grid-cols-2 gap-3">
          {(Object.entries(policy) as [string, number][]).map(([k, v]) => (
            <div key={k}>
              <label className={labelClass}>{k.replace(/_/g, ' ')}</label>
              <input type="number" className={inputClass} value={v}
                onChange={e => setPolicy(p => ({ ...p, [k]: Number(e.target.value) }))} />
            </div>
          ))}
        </div>
        <button onClick={handleSuggest} disabled={suggestLoading}
          className="w-full border border-green-300 text-green-700 hover:bg-green-50 font-medium py-2 rounded-lg text-sm transition-colors disabled:opacity-50">
          {suggestLoading ? 'Asking AI…' : 'Get AI Policy Suggestions'}
        </button>
        {suggestion && (
          <div className="bg-purple-50 border border-purple-100 rounded-lg p-3 text-sm text-gray-700 leading-relaxed">
            {suggestion}
          </div>
        )}
      </section>

      {/* Compliance Doc Analyzer */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
        <div>
          <h2 className="font-semibold text-gray-800">Compliance Document Analyzer</h2>
          <p className="text-xs text-gray-500 mt-0.5">Paste document text to extract entities and verify compliance fields via AI.</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={labelClass}>Document Type</label>
            <select className={inputClass} value={docType} onChange={e => setDocType(e.target.value)}>
              <option value="certificate">Certificate</option>
              <option value="invoice">Invoice</option>
              <option value="chain_of_custody">Chain of Custody</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Region</label>
            <input className={inputClass} value={docRegion} onChange={e => setDocRegion(e.target.value)} placeholder="e.g. India" />
          </div>
          <div className="col-span-2">
            <label className={labelClass}>Asset ID (optional)</label>
            <input className={inputClass} value={docAssetId} onChange={e => setDocAssetId(e.target.value)} placeholder="e.g. ASSET-abc123" />
          </div>
        </div>
        <div>
          <label className={labelClass}>Document Text *</label>
          <textarea
            rows={6}
            className={inputClass}
            value={docContent}
            onChange={e => setDocContent(e.target.value)}
            placeholder="Paste the extracted text content of the compliance document here…"
          />
        </div>
        <button
          onClick={handleAnalyzeDoc}
          disabled={docLoading || !docContent.trim()}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 rounded-lg text-sm transition-colors disabled:opacity-50"
        >
          {docLoading ? 'Analysing…' : 'Analyse Document'}
        </button>
        {docResult && (
          <div className="space-y-3">
            <div className={`rounded-lg px-3 py-2 text-sm font-semibold ${
              docResult.verification_status === 'VERIFIED' ? 'bg-green-50 text-green-700' :
              docResult.verification_status === 'REJECTED' ? 'bg-red-50 text-red-700' : 'bg-yellow-50 text-yellow-700'
            }`}>
              Status: {docResult.verification_status}
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">{docResult.summary}</p>
            {Object.keys(docResult.extracted_entities).length > 0 && (
              <div className="bg-gray-50 rounded-lg p-3 text-xs space-y-1">
                <p className="font-semibold text-gray-600 mb-1">Extracted Fields</p>
                {Object.entries(docResult.extracted_entities).map(([k, v]) => (
                  <div key={k} className="flex gap-2">
                    <span className="text-gray-500 capitalize min-w-[140px]">{k.replace(/_/g, ' ')}</span>
                    <span className={`font-medium ${v === 'UNCLEAR' ? 'text-yellow-600' : 'text-gray-800'}`}>{v}</span>
                  </div>
                ))}
              </div>
            )}
            {docResult.missing_fields.length > 0 && (
              <div className="bg-red-50 border border-red-100 rounded-lg p-3 text-xs">
                <p className="font-semibold text-red-700 mb-1">Missing Fields</p>
                <ul className="list-disc list-inside space-y-0.5 text-red-600">
                  {docResult.missing_fields.map(f => <li key={f}>{f.replace(/_/g, ' ')}</li>)}
                </ul>
              </div>
            )}
            {docResult.recommendations.length > 0 && (
              <div className="bg-amber-50 border border-amber-100 rounded-lg p-3 text-xs">
                <p className="font-semibold text-amber-700 mb-1">Recommendations</p>
                <ul className="list-disc list-inside space-y-0.5 text-amber-700">
                  {docResult.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      {/* About */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
        <h2 className="font-semibold text-gray-800 mb-3">About</h2>
        <dl className="space-y-1.5 text-sm">
          {[
            ['Version', '2.0.0'],
            ['ML Model', 'Gradient Boosting (AUC-ROC 0.9962)'],
            ['LLM', 'Amazon Bedrock · Qwen3 30B'],
            ['Database', 'SQLite (SQLAlchemy ORM)'],
            ['Frontend', 'React 18 + Vite + TailwindCSS'],
          ].map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <dt className="text-gray-500">{k}</dt>
              <dd className="font-medium text-gray-700">{v}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
