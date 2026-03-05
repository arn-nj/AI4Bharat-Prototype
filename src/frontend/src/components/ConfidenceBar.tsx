interface ConfidenceBarProps {
  score: number; // 0–1
  band?: string;
}

export default function ConfidenceBar({ score, band }: ConfidenceBarProps) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 70 ? 'bg-green-500' :
    pct >= 40 ? 'bg-yellow-500' :
                'bg-red-400';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-10 text-right">
        {pct}%{band ? ` (${band})` : ''}
      </span>
    </div>
  );
}
