import { type ReactNode, useState } from 'react';
import type { AuthSession } from '../types/auth';
import type { WorkspaceView } from '../types/workspace';
import { ProjectExplorer } from './ProjectExplorer';
import { StatusBadge } from './StatusBadge';

interface StudioChromeProps {
  session: AuthSession;
  activeView: WorkspaceView;
  isMachineReady: boolean;
  isRunning: boolean;
  children: ReactNode;
  onViewChange: (view: WorkspaceView) => void;
  onRunToggle: () => void;
  onRefresh: () => void;
  onSignOut: () => void;
}

const TOP_VIEWS: Array<{ label: string; view: WorkspaceView }> = [
  { label: 'Workspace', view: 'dashboard' },
  { label: 'Database', view: 'database' },
  { label: 'Research', view: 'research' },
  { label: 'Hardware', view: 'hardware' },
  { label: 'Settings', view: 'settings' },
];

export function StudioChrome({
  session,
  activeView,
  isMachineReady,
  isRunning,
  children,
  onViewChange,
  onRunToggle,
  onRefresh,
  onSignOut,
}: StudioChromeProps) {
  const [isExplorerCollapsed, setIsExplorerCollapsed] = useState(false);

  return (
    <main className="studio-shell">
      <header className="studio-topbar">
        <button className="studio-brand" type="button" onClick={() => onViewChange('dashboard')}>
          <span className="studio-brand__mark" aria-hidden="true">A</span>
          <span>AOI Studio</span>
        </button>
        <nav className="studio-menu" aria-label="Main navigation">
          {TOP_VIEWS.map((item) => (
            <button
              type="button"
              key={item.view}
              className={activeView === item.view ? 'studio-menu__active' : ''}
              onClick={() => onViewChange(item.view)}
            >
              {item.label}
            </button>
          ))}
          <button type="button" disabled title="Reports are not available in this milestone">Reports</button>
        </nav>
        <div className="studio-account">
          <StatusBadge status={isMachineReady ? 'success' : 'warning'} label={isMachineReady ? 'Ready' : 'Check I/O'} />
          <span className="studio-account__identity">
            <strong>{session.user.fullName}</strong>
            <small>Operator · Admin</small>
          </span>
          <button className="text-action" type="button" onClick={onSignOut}>Sign out</button>
        </div>
      </header>

      <section className="studio-toolbar" aria-label="Inspection controls">
        <button className={`tool-button ${isRunning ? 'tool-button--stop' : 'tool-button--run'}`} type="button" onClick={onRunToggle}>
          <span aria-hidden="true">{isRunning ? '■' : '▶'}</span>
          {isRunning ? 'Stop' : 'Run'}
        </button>
        <button className="tool-button" type="button" disabled title="Single-step execution is not available in this milestone"><span aria-hidden="true">▷</span> Single step</button>
        <button className="tool-button" type="button" disabled title="Camera capture is not available in this milestone"><span aria-hidden="true">▣</span> Capture</button>
        <button className="tool-button" type="button" onClick={() => onViewChange('camera-manager')}><span aria-hidden="true">◎</span> Calibrate</button>
        <button className="tool-button" type="button" onClick={onRefresh}><span aria-hidden="true">↻</span> Refresh I/O</button>
        <span className="studio-toolbar__spacer" />
        <div className="mode-switch" aria-label="Workspace mode">
          <span className="mode-switch__active">Production</span>
          <span>Research</span>
        </div>
      </section>

      <div className={`studio-body ${isExplorerCollapsed ? 'studio-body--explorer-collapsed' : ''}`}>
        <ProjectExplorer
          activeView={activeView}
          isCollapsed={isExplorerCollapsed}
          onViewChange={onViewChange}
          onCollapseToggle={() => setIsExplorerCollapsed((currentValue) => !currentValue)}
        />
        <section className="studio-workspace">{children}</section>
      </div>

      <footer className="studio-dock">
        <span>Timeline</span>
        <span>Logs</span>
        <span>Performance</span>
        <span>Data provenance</span>
        <span className="studio-dock__spacer" />
        <strong>Yield: 99.1%</strong>
        <strong>Cycle: 0.42s</strong>
        <strong>Queue: 54</strong>
        <span className="studio-dock__healthy">0 Alerts</span>
      </footer>
    </main>
  );
}