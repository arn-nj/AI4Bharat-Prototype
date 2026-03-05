interface RiskBadgeProps {
  level: string;
}

const STYLES: Record<string, string> = {
  high:   'bg-red-100 text-red-700 border border-red-200',
  medium: 'bg-yellow-100 text-yellow-700 border border-yellow-200',
  low:    'bg-green-100 text-green-700 border border-green-200',
};

export default function RiskBadge({ level }: RiskBadgeProps) {
  const styles = STYLES[level?.toLowerCase()] ?? 'bg-gray-100 text-gray-700';
  return (
    <span className={`inline-flex items-center rounded-full text-xs font-semibold px-2.5 py-0.5 uppercase ${styles}`}>
      {level}
    </span>
  );
}
