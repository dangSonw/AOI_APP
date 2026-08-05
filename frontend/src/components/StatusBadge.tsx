import type { InspectionStatus } from '../types/workspace';

interface StatusBadgeProps {
  status: InspectionStatus;
  label: string;
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-badge--${status}`}>
      <span className="status-badge__dot" aria-hidden="true" />
      {label}
    </span>
  );
}