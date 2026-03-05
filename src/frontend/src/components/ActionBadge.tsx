interface ActionBadgeProps {
  action: string;
  size?: 'sm' | 'md';
}

const ACTION_STYLES: Record<string, string> = {
  recycle:   'bg-red-100 text-red-700',
  repair:    'bg-orange-100 text-orange-700',
  refurbish: 'bg-yellow-100 text-yellow-700',
  redeploy:  'bg-blue-100 text-blue-700',
  resale:    'bg-green-100 text-green-700',
};

export default function ActionBadge({ action, size = 'md' }: ActionBadgeProps) {
  const styles = ACTION_STYLES[action.toLowerCase()] ?? 'bg-gray-100 text-gray-700';
  const sizeClass = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1';
  return (
    <span className={`inline-flex items-center rounded-full font-medium capitalize ${styles} ${sizeClass}`}>
      {action}
    </span>
  );
}
