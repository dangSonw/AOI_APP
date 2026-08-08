import type { WorkspaceView } from '../types/workspace';

interface ProjectExplorerProps {
  activeView: WorkspaceView;
  isCollapsed: boolean;
  onViewChange: (view: WorkspaceView) => void;
  onCollapseToggle: () => void;
}

const EXPLORER_ITEMS: Array<{
  label: string;
  icon: string;
  view?: WorkspaceView;
  isExpanded?: boolean;
}> = [
  { label: 'Project', icon: 'P', view: 'dashboard', isExpanded: true },
  { label: 'Hardware', icon: 'H', view: 'hardware' },
  { label: 'Camera rig', icon: 'C', view: 'camera-manager' },
  { label: 'Workflow', icon: 'W', view: 'workflow-editor' },
  { label: 'Models', icon: 'M', view: 'research', isExpanded: true },
  { label: 'Dataset', icon: 'D', view: 'dataset' },
  { label: 'Database', icon: 'DB', view: 'database' },
  { label: 'Plugins', icon: 'PL' },
  { label: 'Logs', icon: 'L' },
  { label: 'Settings', icon: 'S', view: 'settings' },
];

export function ProjectExplorer({ activeView, isCollapsed, onViewChange, onCollapseToggle }: ProjectExplorerProps) {
  return (
    <aside className={`project-explorer ${isCollapsed ? 'project-explorer--collapsed' : ''}`} aria-label="Project explorer">
      <div className="panel-heading">
        <span>Project explorer</span>
        <button
          className="icon-button"
          type="button"
          aria-label={isCollapsed ? 'Expand project explorer' : 'Collapse project explorer'}
          aria-expanded={!isCollapsed}
          onClick={onCollapseToggle}
        >
          {isCollapsed ? '›' : '‹'}
        </button>
      </div>
      <nav className="project-tree" aria-label="Workspace views">
        {EXPLORER_ITEMS.map((item) => {
          const isActive = item.view === activeView;
          return (
            <button
              className={`project-tree__item ${isActive ? 'project-tree__item--active' : ''}`}
              type="button"
              key={item.label}
              disabled={!item.view}
              aria-current={isActive ? 'page' : undefined}
              onClick={() => item.view && onViewChange(item.view)}
            >
              <span className="project-tree__chevron" aria-hidden="true">
                {item.isExpanded ? '⌄' : item.view ? '›' : '·'}
              </span>
              <span className="project-tree__icon" aria-hidden="true">{item.icon}</span>
              <span className="project-tree__label">{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="project-explorer__recipe">
        <span className="overline">Active recipe</span>
        <strong>Rev C · Mainboard</strong>
        <span>v2.14 · Production</span>
      </div>
    </aside>
  );
}