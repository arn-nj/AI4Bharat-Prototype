import type { Scenario } from '../types'

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <tr className="even:bg-gray-50">
      <td className="py-1.5 pr-4 text-sm text-gray-500 font-medium whitespace-nowrap">{label}</td>
      <td className="py-1.5 text-sm text-gray-900">{value}</td>
    </tr>
  )
}

export function DeviceTable({ scenario }: { scenario: Scenario }) {
  const lowCompleteness = scenario.data_completeness < 0.6

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Device Characteristics</h2>
      {lowCompleteness && (
        <div className="mb-3 rounded bg-blue-50 border border-blue-200 px-4 py-2 text-sm text-blue-800">
          Data completeness is below 60%. The ML model will be skipped — the Policy engine runs independently.
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Identity & Usage */}
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase mb-2">Identity &amp; Usage</p>
          <table className="w-full">
            <tbody>
              <Row label="Asset ID"           value={scenario.asset_id} />
              <Row label="Device Type"        value={scenario.device_type} />
              <Row label="Brand"              value={scenario.brand} />
              <Row label="Department"         value={scenario.department} />
              <Row label="Region"             value={scenario.region} />
              <Row label="OS"                 value={scenario.os} />
              <Row label="Usage Type"         value={scenario.usage_type} />
              <Row label="Model Year"         value={scenario.model_year} />
              <Row label="Age (months)"       value={scenario.age_in_months} />
              <Row label="Daily Usage Hours"  value={`${scenario.daily_usage_hours} h`} />
              <Row label="Performance Rating" value={`${scenario.performance_rating} / 5`} />
            </tbody>
          </table>
        </div>
        {/* Right: Hardware Health */}
        <div>
          <p className="text-xs font-semibold text-gray-400 uppercase mb-2">Hardware Health &amp; Incidents</p>
          <table className="w-full">
            <tbody>
              <Row label="Battery Health"            value={`${scenario.battery_health_percent}%`} />
              <Row label="Battery Cycles"            value={scenario.battery_cycles} />
              <Row label="SMART Sectors Reallocated" value={scenario.smart_sectors_reallocated} />
              <Row label="Thermal Events (90d)"      value={scenario.thermal_events_count} />
              <Row label="Overheating Issues"        value={scenario.overheating_issues} />
              <Row label="Total Incidents (90d)"     value={scenario.total_incidents} />
              <Row label="Critical Incidents"        value={scenario.critical_incidents} />
              <Row label="High Incidents"            value={scenario.high_incidents} />
              <Row label="Medium Incidents"          value={scenario.medium_incidents} />
              <Row label="Low Incidents"             value={scenario.low_incidents} />
              <Row label="Avg Resolution Time"       value={`${scenario.avg_resolution_time_hours} h`} />
              <Row label="Data Completeness"         value={`${(scenario.data_completeness * 100).toFixed(0)}%`} />
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
