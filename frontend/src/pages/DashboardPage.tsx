import type { PhysicalInputState, PhysicalOutputState } from '../types/physical-io';
import type { InspectionStatus } from '../types/workspace';
import type { InspectionRun } from '../types/inspection';
import { StatusBadge } from '../components/StatusBadge';
import type { Workflow } from '../types/workflow';
import type { AlgorithmDefinition } from '../types/workflow';
import type { DashboardPreferences, ViewerPreference } from '../types/workstation-preferences';
import { CollapsiblePanelHeader } from '../components/CollapsiblePanelHeader';
import { ViewerSizeControls } from '../components/ViewerSizeControls';

interface DashboardPageProps {
  inputs: PhysicalInputState | null;
  outputs: PhysicalOutputState | null;
  isLoading: boolean;
  error: string;
  isRunning: boolean;
  inspectionRun: InspectionRun | null;
  runError: string;
  onOutputToggle: (signalName: string, currentValue: boolean) => void;
  workflow: Workflow | null;
  workflowError: string;
  onConfigureWorkflow: () => void;
  catalog: AlgorithmDefinition[];
  preferences: DashboardPreferences;
  onPreferencesChange: (preferences: DashboardPreferences) => void;
}

const METRICS = [
  { label: 'First-pass yield', value: '99.1', unit: '%', delta: '+0.4%' },
  { label: 'Cycle time', value: '0.42', unit: 's', delta: '-18 ms' },
  { label: 'Queue', value: '54', unit: 'boards', delta: '12 min' },
  { label: 'Inspected', value: '1,247', unit: 'today', delta: '+5.2%' },
  { label: 'Defects', value: '12', unit: 'flagged', delta: '0.96%' },
];

export function DashboardPage({ inputs, outputs, isLoading, error, isRunning, inspectionRun, runError, onOutputToggle, workflow, workflowError, onConfigureWorkflow, catalog, preferences, onPreferencesChange }: DashboardPageProps) {
  const panels = preferences.panels;
  const updatePanel = <K extends keyof typeof panels>(key: K, value: typeof panels[K]) => onPreferencesChange({ panels: { ...panels, [key]: value } });
  const togglePanel = (key: keyof typeof panels) => updatePanel(key, { ...panels[key], isCollapsed: !panels[key].isCollapsed });
  const lineStatus: InspectionStatus = isRunning ? 'running' : inputs ? (inputs.machine.emergencyStop ? 'error' : 'success') : 'warning';
  const lineStatusLabel = isRunning ? 'Inspection running' : inputs ? (inputs.machine.emergencyStop ? 'Emergency stop' : 'Line ready') : 'Awaiting I/O';
  const systemStatuses = [
    { label: 'Machine', status: inputs ? (inputs.machine.emergencyStop ? 'error' : 'success') : 'warning' },
    { label: 'Camera', status: inputs?.sensors.cameraReady ? 'success' : 'warning' },
    { label: 'PLC', status: inputs?.machine.doorClosed ? 'success' : 'warning' },
    { label: 'Lighting', status: outputs ? (outputs.signals.towerLightRed ? 'error' : 'success') : 'warning' },
    { label: 'Model', status: 'success' },
    { label: 'Recipe', status: 'success' },
  ] as const;
  const workflowNodes = new Map(workflow?.nodes.map((node) => [node.id, node]) ?? []);
  const orderedWorkflowNodes = workflow?.executionOrder
    .map((nodeId) => workflowNodes.get(nodeId))
    .filter((node) => node !== undefined) ?? [];

  return (
    <div className="dashboard-layout" aria-busy={isLoading}>
      <div className="dashboard-main">
        {error && <p className="studio-message studio-message--error" role="alert">{error}</p>}
        {runError && <p className="studio-message studio-message--error" role="alert">{runError}</p>}

        <section className={`dashboard-panel dashboard-state ${panels.state.isCollapsed ? 'dashboard-panel--collapsed' : ''}`}>
          <CollapsiblePanelHeader title="State" isCollapsed={panels.state.isCollapsed} onToggle={() => togglePanel('state')} status={<StatusBadge status={lineStatus} label={lineStatusLabel} />} />
          {!panels.state.isCollapsed && <>
          {inspectionRun && (
            <section className={`inspection-runtime inspection-runtime--${inspectionRun.status}`} aria-label="Persisted inspection runtime" aria-live="polite">
              <div className="inspection-runtime__identity">
                <span className="overline">Run evidence</span>
                <strong>{inspectionRun.boardSerial}</strong>
                <code title={inspectionRun.id}>{inspectionRun.id}</code>
              </div>
              <div className="inspection-runtime__stage">
                <span><strong>{formatRuntimeStep(inspectionRun.currentStep)}</strong><b>{inspectionRun.progressPercent}%</b></span>
                <div className="inspection-runtime__track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={inspectionRun.progressPercent}>
                  <i style={{ width: `${inspectionRun.progressPercent}%` }} />
                </div>
                <small>{inspectionRun.errorMessage ?? runtimeMessage(inspectionRun)}</small>
              </div>
              <div className="inspection-runtime__evidence">
                <span className="overline">Immutable evidence</span>
                <strong>{inspectionRun.decision ?? inspectionRun.status.toUpperCase()}</strong>
                <code title={inspectionRun.evidenceSha256 ?? inspectionRun.workflowSha256}>
                  {(inspectionRun.evidenceSha256 ?? inspectionRun.workflowSha256).slice(0, 16)}…
                </code>
              </div>
            </section>
          )}
          <div className="instrument-rail">
          <section className="system-strip" aria-label="System status">
            {systemStatuses.map((item) => (
              <article className={`system-status system-status--${item.status}`} key={item.label}>
                <span>{item.label}</span>
                <strong>{item.status === 'success' ? 'OK' : item.status === 'error' ? 'ERR' : 'WAIT'}</strong>
              </article>
            ))}
          </section>

          <section className="metric-grid" aria-label="Production metrics">
            {METRICS.map((metric) => (
              <article className="metric-card" key={metric.label}>
                <span className="overline">{metric.label}</span>
                <div><strong>{metric.value}</strong><span>{metric.unit}</span></div>
                <small>{metric.delta} from previous shift</small>
              </article>
            ))}
          </section>
          </div></>}
        </section>

        <section className="viewer-grid" aria-label="Inspection viewers">
          <article className={`inspection-viewer ${panels.optical2D.isCollapsed ? 'dashboard-panel--collapsed' : ''}`} style={{ '--viewer-width': panels.optical2D.widthUnits, '--viewer-height': panels.optical2D.heightUnits } as React.CSSProperties}>
            <CollapsiblePanelHeader title="2D optical view" isCollapsed={panels.optical2D.isCollapsed} onToggle={() => togglePanel('optical2D')} status={<StatusBadge status="success" label="Live" />} controls={<ViewerSizeControls label="2D optical view" viewer={panels.optical2D} onChange={(viewer: ViewerPreference) => updatePanel('optical2D', viewer)} />} />
            {!panels.optical2D.isCollapsed && <>
            <div className="pcb-visual pcb-visual--optical" role="img" aria-label="Simulated top-down PCB optical inspection">
              <span className="pcb-visual__board" />
              <span className="pcb-visual__roi pcb-visual__roi--one">ROI 03</span>
              <span className="pcb-visual__roi pcb-visual__roi--two">ROI 07</span>
              <span className="viewer-reticle" aria-hidden="true">+</span>
            </div>
            <footer><span>Top camera · 12 MP</span><span>8.0 ms · Gain 1.2</span></footer>
            </>}
          </article>

          <article className={`inspection-viewer ${panels.heightmap3D.isCollapsed ? 'dashboard-panel--collapsed' : ''}`} style={{ '--viewer-width': panels.heightmap3D.widthUnits, '--viewer-height': panels.heightmap3D.heightUnits } as React.CSSProperties}>
            <CollapsiblePanelHeader title="3D component heightmap" isCollapsed={panels.heightmap3D.isCollapsed} onToggle={() => togglePanel('heightmap3D')} status={<StatusBadge status="success" label="Synced" />} controls={<ViewerSizeControls label="3D component heightmap" viewer={panels.heightmap3D} onChange={(viewer: ViewerPreference) => updatePanel('heightmap3D', viewer)} />} />
            {!panels.heightmap3D.isCollapsed && <>
            <div className="pcb-visual pcb-visual--depth" role="img" aria-label="Simulated PCB component depth map">
              <span className="depth-plane" />
              <span className="depth-component depth-component--one" />
              <span className="depth-component depth-component--two" />
              <span className="depth-component depth-component--three" />
              <span className="depth-scale">0 μm<span />2400 μm</span>
            </div>
            <footer><span>Photometric stereo</span><span>RMSE 0.18°</span></footer>
            </>}
          </article>
        </section>

        <section className={`io-console ${panels.physicalIo.isCollapsed ? 'dashboard-panel--collapsed' : ''}`}>
          <CollapsiblePanelHeader title="Physical I/O" isCollapsed={panels.physicalIo.isCollapsed} onToggle={() => togglePanel('physicalIo')} status={<span>Revision {outputs?.revision ?? inputs?.revision ?? '—'}</span>} />
          {!panels.physicalIo.isCollapsed && <div className="io-console__signals">
            {outputs && Object.entries(outputs.signals).map(([name, value]) => (
              <button
                type="button"
                key={name}
                className={value === true ? 'io-signal io-signal--active' : 'io-signal'}
                disabled={typeof value !== 'boolean'}
                onClick={() => typeof value === 'boolean' && onOutputToggle(name, value)}
              >
                <span aria-hidden="true" />
                {formatSignalName(name)}
              </button>
            ))}
          </div>}
        </section>
      </div>

      <aside className={`pipeline-panel ${panels.inspectionFlow.isCollapsed ? 'pipeline-panel--collapsed' : ''}`} aria-label="Inspection flow">
        <div className="panel-heading">
          <span>Inspection flow</span>
          <span className="pipeline-panel__actions">
            <button className="icon-button" type="button" aria-label="Configure inspection workflow" onClick={onConfigureWorkflow}>⚙</button>
            <button
              className="icon-button"
              type="button"
              aria-label={panels.inspectionFlow.isCollapsed ? 'Expand inspection flow' : 'Collapse inspection flow'}
              aria-expanded={!panels.inspectionFlow.isCollapsed}
              onClick={() => togglePanel('inspectionFlow')}
            >
              {panels.inspectionFlow.isCollapsed ? '‹' : '›'}
            </button>
          </span>
        </div>
        {workflowError && <p className="pipeline-panel__error" role="status">{workflowError}</p>}
        {!workflowError && orderedWorkflowNodes.length === 0 && <p className="pipeline-panel__error">No configured workflow steps.</p>}
        <ol className="pipeline-list">
          {orderedWorkflowNodes.map((step, index) => (
            <li className="pipeline-step pipeline-step--configuration" key={step.id}>
              <span className="pipeline-step__index">{String(index + 1).padStart(2, '0')}</span>
              <span><strong>{step.displayName}</strong><small>{catalog.find((definition) => definition.id === step.algorithmId)?.use ?? 'test'}</small></span>
              <code>{step.algorithmId}</code>
            </li>
          ))}
        </ol>
        <section className="pipeline-summary">
          <span className="overline">Saved recipe graph</span>
          <strong>R{workflow?.revision ?? '—'}</strong>
          <span>{workflow ? `${workflow.nodes.length} nodes · Schema v${workflow.version}` : 'Workflow unavailable'}</span>
        </section>
      </aside>
    </div>
  );
}

function formatSignalName(name: string): string {
  return name.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/^./, (character) => character.toUpperCase());
}

function formatRuntimeStep(step: string): string {
  return step.replace(/-/g, ' ').replace(/^./, (character: string) => character.toUpperCase());
}

function runtimeMessage(run: InspectionRun): string {
  if (run.status === 'completed') return `Persisted ${run.nodeRuns.length} node evidence record${run.nodeRuns.length === 1 ? '' : 's'}.`;
  if (run.status === 'cancelled') return 'Run cancelled at a persisted safe checkpoint.';
  if (run.status === 'faulted') return run.errorCode ?? 'Inspection runtime faulted.';
  if (run.cancelRequested) return 'Cancellation requested. Waiting for safe checkpoint.';
  return 'Motion, capture, artifact, and node evidence persist at each stage.';
}