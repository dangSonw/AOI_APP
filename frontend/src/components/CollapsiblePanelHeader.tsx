import type { ReactNode } from 'react';


interface CollapsiblePanelHeaderProps {
  title: string;
  isCollapsed: boolean;
  onToggle: () => void;
  status?: ReactNode;
  controls?: ReactNode;
}

export function CollapsiblePanelHeader({ title, isCollapsed, onToggle, status, controls }: CollapsiblePanelHeaderProps) {
  return (
    <header className="collapsible-panel__header">
      <strong>{title}</strong>
      <span className="collapsible-panel__actions">
        {status}
        {controls}
        <button
          type="button"
          className="icon-button"
          aria-label={`${isCollapsed ? 'Expand' : 'Collapse'} ${title}`}
          aria-expanded={!isCollapsed}
          onClick={onToggle}
        >
          {isCollapsed ? '＋' : '−'}
        </button>
      </span>
    </header>
  );
}