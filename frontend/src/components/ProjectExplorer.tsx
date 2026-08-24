import type { WorkspaceView } from '../types/workspace';

interface ProjectExplorerProps {
  activeView: WorkspaceView;
  isCollapsed: boolean;
  onViewChange: (view: WorkspaceView) => void;
  onCollapseToggle: () => void;
}

const EXPLORER_GROUPS: Array<{
  label: string;
  items: Array<{ label: string; icon: string; view: WorkspaceView }>;
}> = [
  {
    label: 'Operate',
    items: [
      { label: 'Dashboard', icon: 'P', view: 'dashboard' },
      { label: 'Hardware', icon: 'H', view: 'hardware' },
      { label: 'Camera rig', icon: 'C', view: 'camera-manager' },
    ],
  },
  {
    label: 'Build',
    items: [
      { label: 'Workflow', icon: 'W', view: 'workflow-editor' },
      { label: 'Dataset', icon: 'D', view: 'dataset' },
    ],
  },
  {
    label: 'Review',
    items: [
      { label: 'Database', icon: 'DB', view: 'database' },
      { label: 'Research', icon: 'R', view: 'research' },
      { label: 'Models', icon: 'M', view: 'models' },
    ],
  },
  {
    label: 'System',
    items: [
      { label: 'Help', icon: '?', view: 'help' },
      { label: 'Settings', icon: 'S', view: 'settings' },
    ],
  },
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
        {EXPLORER_GROUPS.map((group) => (
          <section className="project-tree__group" key={group.label} aria-label={group.label}>
            <h2 className="project-tree__group-label">{group.label}</h2>
            {group.items.map((item) => {
              const isActive = item.view === activeView;
              return (
                <button
                  className={`project-tree__item ${isActive ? 'project-tree__item--active' : ''}`}
                  type="button"
                  key={item.label}
                  aria-current={isActive ? 'page' : undefined}
                  onClick={() => onViewChange(item.view)}
                >
                  <span className="project-tree__icon" aria-hidden="true">{item.icon}</span>
                  <span className="project-tree__label">{item.label}</span>
                </button>
              );
            })}
          </section>
        ))}
      </nav>
    </aside>
  );
}