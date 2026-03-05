/**
 * Corporate IT asset tag generator
 *
 * Format: [REGION]-[DEPT]-[TYPE]-[SERIAL]
 * Example: BLR-SALES-LT-A3F2
 *
 * Matches conventions used in enterprise ITSM systems (ServiceNow, Jira Assets, etc.)
 * where the tag encodes location, cost-centre, device class, and a short serial.
 */

const REGION_CODES: Record<string, string> = {
  'mumbai':      'MUM',
  'bengaluru':   'BLR',
  'bangalore':   'BLR',
  'chennai':     'MAA',
  'hyderabad':   'HYD',
  'delhi ncr':   'DEL',
  'delhi':       'DEL',
  'pune':        'PNQ',
  'kolkata':     'CCU',
  'ahmedabad':   'AMD',
  'kochi':       'COK',
  'noida':       'NOI',
};

const DEVICE_CODES: Record<string, string> = {
  'laptop':          'LT',
  'desktop':         'DT',
  'server':          'SRV',
  'tablet':          'TB',
  'workstation':     'WS',
  'printer':         'PRN',
  'network device':  'NET',
  'mobile phone':    'MOB',
  'monitor':         'MON',
  'projector':       'PJT',
};

/**
 * Derives a short department code — takes first letter of each word up to 4 chars.
 * "Delhi NCR" → "DEL", "Sales" → "SLS", "Human Resources" → "HR"
 */
function deptCode(department: string): string {
  const words = department.trim().split(/\s+/);
  if (words.length === 1) {
    // Single word: consonant-skeleton, max 4 chars
    const raw = words[0].toUpperCase().replace(/[AEIOU]/g, '').slice(0, 4);
    return raw.length >= 2 ? raw : words[0].toUpperCase().slice(0, 4);
  }
  // Multi-word: initials
  return words.map(w => w[0]).join('').toUpperCase().slice(0, 4);
}

/**
 * Serial segment: use the real serial number if present (last 6 chars, uppercased),
 * otherwise fall back to last 4 hex chars of the UUID.
 */
function serialCode(assetId: string, serialNumber?: string | null): string {
  if (serialNumber) {
    return serialNumber.replace(/\s+/g, '').toUpperCase();
  }
  return assetId.replace(/-/g, '').slice(-4).toUpperCase();
}

export function assetTag(asset: {
  asset_id: string;
  device_type: string;
  department: string;
  region: string;
  serial_number?: string | null;
}): string {
  const region = REGION_CODES[asset.region.toLowerCase()] ??
    asset.region.replace(/\s+/g, '').toUpperCase().slice(0, 3);
  const dept   = deptCode(asset.department);
  const type   = DEVICE_CODES[asset.device_type.toLowerCase()] ??
    asset.device_type.replace(/\s+/g, '').toUpperCase().slice(0, 3);
  const serial = serialCode(asset.asset_id, asset.serial_number);

  return `${region}-${dept}-${type}-${serial}`;
}
