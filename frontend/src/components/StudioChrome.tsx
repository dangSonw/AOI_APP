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
  isRunControlBusy?: boolean;
  children: ReactNode;
  onViewChange: (view: WorkspaceView) => void;
  onRunToggle: () => void;
  onRefresh: () => void;
  onSignOut: () => void;
}

export function StudioChrome({
  session,
  activeView,
  isMachineReady,
  isRunning,
  isRunControlBusy = false,
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
        <button
          className={`tool-button ${isRunning ? 'tool-button--stop' : 'tool-button--run'}`}
          type="button"
          disabled={isRunControlBusy}
          aria-busy={isRunControlBusy}
          onClick={onRunToggle}
        >
          <span aria-hidden="true">{isRunning ? '■' : '▶'}</span>
          {isRunControlBusy ? 'Working…' : isRunning ? 'Stop' : 'Run'}
        </button>
        <button className="tool-button" type="button" onClick={() => onViewChange('camera-manager')}><span aria-hidden="true">◎</span> Calibrate</button>
        <button className="tool-button" type="button" onClick={onRefresh}><span aria-hidden="true">↻</span> Refresh I/O</button>
        <span className="studio-toolbar__spacer" />
        <span className="studio-toolbar__hint">Use Workflow to configure the active recipe</span>
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

    </main>
  );
}