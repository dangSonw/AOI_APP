import { useEffect, useState } from 'react';
import type { PhysicalInputState, PhysicalOutputState } from '../types/physical-io';
import type { InspectionStatus } from '../types/workspace';
import type { InspectionRun } from '../types/inspection';
import { StatusBadge } from '../components/StatusBadge';
import type { AlgorithmDefinition, Workflow } from '../types/workflow';
import type { DashboardPreferences, ViewerPreference } from '../types/workstation-preferences';
import { CollapsiblePanelHeader } from '../components/CollapsiblePanelHeader';
import { ViewerSizeControls } from '../components/ViewerSizeControls';
import { readInspectionPreview } from '../services/inspection-service';
import { getDashboardViewerPreference, updateDashboardViewerPreference } from '../utils/workstation-preferences';
import { selectWorkflowOutputViewers } from '../utils/workflow-output-viewers';
import { StructuredArtifactViewer } from '../components/visualization/StructuredVisualization';

interface DashboardPageProps {
  accessToken: string;
  inputs: PhysicalInputState | null;
  outputs: PhysicalOutputState | null;
  isLoading: boolean;
  error: string;
  isRunning: boolean;
  inspectionRun: InspectionRun | null;
  runError: string;
  onOutputToggle: (signalName: string, currentValue: boolean) => void;
  workflow: Workflow | null;
  algorithmCatalog?: AlgorithmDefinition[];
  workflowError: string;
  onConfigureWorkflow: () => void;
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

const WORKFLOW_POPUP_LIMIT = 3;
const WORKFLOW_POPUP_TTL_MS = 3000;

interface WorkflowPopupToast {
  id: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  expiresAt: number;
}

interface WorkflowPopupState {
  seen: string[];
  active: WorkflowPopupToast[];
}

export function DashboardPage({ accessToken, inputs, outputs, isLoading, error, isRunning, inspectionRun, runError, onOutputToggle, workflow, algorithmCatalog = [], workflowError, onConfigureWorkflow, preferences, onPreferencesChange }: DashboardPageProps) {
  const panels = preferences.panels;
  const updatePanel = <K extends keyof typeof panels>(key: K, value: typeof panels[K]) => onPreferencesChange({ panels: { ...panels, [key]: value } });
  const togglePanel = (key: 'state' | 'optical2D' | 'heightmap3D' | 'physicalIo' | 'inspectionFlow') => {
    const panel = panels[key];
    updatePanel(key, { ...panel, isCollapsed: !panel.isCollapsed });
  };
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
  const outputViewers = selectWorkflowOutputViewers(workflow, algorithmCatalog, inspectionRun?.nodeRuns ?? []);
  const updateOutputViewer = (key: string, viewer: ViewerPreference) => onPreferencesChange(
    updateDashboardViewerPreference(preferences, key, viewer),
  );
  const isFlowActive = Boolean(inspectionRun && ['queued', 'precheck', 'capturing', 'executing'].includes(inspectionRun.status));
  const latestNodeRuns = new Map<string, InspectionRun['nodeRuns'][number]>();
  if (inspectionRun) {
    for (const nodeRun of inspectionRun.nodeRuns) {
      const current = latestNodeRuns.get(nodeRun.nodeId);
      if (!current || nodeRun.sequence > current.sequence) latestNodeRuns.set(nodeRun.nodeId, nodeRun);
    }
  }

  const [popupState, setPopupState] = useState<WorkflowPopupState>({ seen: [], active: [] });
  if (inspectionRun) {
    const seen = new Set(popupState.seen);
    const fresh: WorkflowPopupToast[] = [];
    for (const nodeRun of inspectionRun.nodeRuns) {
      if (nodeRun.logEvent?.destination !== 'popup') continue;
      const id = `${inspectionRun.id}:${nodeRun.sequence}`;
      if (seen.has(id)) continue;
      seen.add(id);
      fresh.push({
        id,
        level: nodeRun.logEvent.level,
        message: nodeRun.logEvent.message,
        expiresAt: Date.now() + WORKFLOW_POPUP_TTL_MS,
      });
    }
    if (fresh.length > 0) {
      setPopupState({
        seen: [...seen].slice(-256),
        active: [...fresh.reverse(), ...popupState.active].slice(0, WORKFLOW_POPUP_LIMIT),
      });
    }
  }
  const workflowPopups = popupState.active;

  useEffect(() => {
    if (workflowPopups.length === 0) return;
    const oldest = workflowPopups[workflowPopups.length - 1];
    const remaining = Math.max(oldest.expiresAt - Date.now(), 0);
    const timer = window.setTimeout(() => {
      setPopupState((current) => ({ ...current, active: current.active.filter((toast) => toast.id !== oldest.id) }));
    }, remaining);
    return () => window.clearTimeout(timer);
  }, [workflowPopups]);

  return (
    <div className="dashboard-layout" aria-busy={isLoading}>
      {workflowPopups.length > 0 && (
        <div className="workflow-log-popups" role="status" aria-live="polite">
          {workflowPopups.map((toast) => (
            <div key={toast.id} className={`workflow-log-popup workflow-log-popup--${toast.level}`}>
              <span><strong>{toast.level.toUpperCase()}</strong> {toast.message}</span>
            </div>
          ))}
        </div>
      )}
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
          {outputViewers.twoD.map((output) => {
            const viewer = getDashboardViewerPreference(preferences, output.key);
            return (
              <article className={`inspection-viewer ${viewer.isCollapsed ? 'dashboard-panel--collapsed' : ''}`} style={{ '--viewer-width': viewer.widthUnits, '--viewer-height': viewer.heightUnits } as React.CSSProperties} key={output.key}>
                <CollapsiblePanelHeader title={`2D optical view · ${output.title}`} isCollapsed={viewer.isCollapsed} onToggle={() => updateOutputViewer(output.key, { ...viewer, isCollapsed: !viewer.isCollapsed })} status={<StatusBadge status={inspectionRun?.status === 'completed' ? 'success' : 'warning'} label={inspectionRun?.status === 'completed' ? 'Workflow output' : 'Awaiting output'} />} controls={<ViewerSizeControls label={`2D optical view ${output.title}`} viewer={viewer} onChange={(nextViewer) => updateOutputViewer(output.key, nextViewer)} />} />
                {!viewer.isCollapsed && <>
                  {output.kind === 'plot-2d'
                    ? <StructuredArtifactViewer accessToken={accessToken} descriptor={output.descriptor} title={output.descriptor?.title ?? output.title} />
                    : <InspectionPreview accessToken={accessToken} run={inspectionRun} nodeId={output.nodeId} />}
                  <footer><span>{output.title}</span><span>{inspectionRun?.nodeRuns.length ?? 0} nodes</span></footer>
                </>}
              </article>
            );
          })}
          {outputViewers.tables.map((output) => {
            const viewer = getDashboardViewerPreference(preferences, output.key);
            return (
              <article className={`inspection-viewer ${viewer.isCollapsed ? 'dashboard-panel--collapsed' : ''}`} style={{ '--viewer-width': viewer.widthUnits, '--viewer-height': viewer.heightUnits } as React.CSSProperties} key={output.key}>
                <CollapsiblePanelHeader title={`Table · ${output.title}`} isCollapsed={viewer.isCollapsed} onToggle={() => updateOutputViewer(output.key, { ...viewer, isCollapsed: !viewer.isCollapsed })} status={<StatusBadge status={output.descriptor ? 'success' : 'warning'} label={output.descriptor ? 'Workflow output' : 'Awaiting output'} />} controls={<ViewerSizeControls label={`Table ${output.title}`} viewer={viewer} onChange={(nextViewer) => updateOutputViewer(output.key, nextViewer)} />} />
                {!viewer.isCollapsed && <>
                  <StructuredArtifactViewer accessToken={accessToken} descriptor={output.descriptor} title={output.descriptor?.title ?? output.title} />
                  <footer><span>{output.title}</span><span>Structured table output</span></footer>
                </>}
              </article>
            );
          })}
          {outputViewers.threeD.map((output) => {
            const viewer = getDashboardViewerPreference(preferences, output.key);
            return (
              <article className={`inspection-viewer ${viewer.isCollapsed ? 'dashboard-panel--collapsed' : ''}`} style={{ '--viewer-width': viewer.widthUnits, '--viewer-height': viewer.heightUnits } as React.CSSProperties} key={output.key}>
                <CollapsiblePanelHeader title={`3D measurement · ${output.title}`} isCollapsed={viewer.isCollapsed} onToggle={() => updateOutputViewer(output.key, { ...viewer, isCollapsed: !viewer.isCollapsed })} status={<StatusBadge status="success" label="Workflow output" />} controls={<ViewerSizeControls label={`3D measurement ${output.title}`} viewer={viewer} onChange={(nextViewer) => updateOutputViewer(output.key, nextViewer)} />} />
                {!viewer.isCollapsed && <>
                  {output.kind === 'heightmap'
                    ? <StructuredArtifactViewer accessToken={accessToken} descriptor={output.descriptor} title={output.descriptor?.title ?? output.title} />
                    : <div className="pcb-visual pcb-visual--depth" role="img" aria-label={`3D measurement output for ${output.title}`}>
                    <span className="depth-plane" />
                    <span className="depth-component depth-component--one" />
                    <span className="depth-component depth-component--two" />
                    <span className="depth-component depth-component--three" />
                    <span className="depth-scale">0 μm<span />2400 μm</span>
                    </div>}
                  <footer><span>{output.title}</span><span>3D measurement output</span></footer>
                </>}
              </article>
            );
          })}
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
          {orderedWorkflowNodes.map((step, index) => {
            const nodeRun = latestNodeRuns.get(step.id);
            const lastRunMs = nodeRun?.durationMs ?? null;
            const runtimeStatus = isFlowActive && nodeRun
              ? nodeRun.status === 'completed'
                ? 'completed'
                : nodeRun.status === 'running'
                  ? 'running'
                  : 'faulted'
              : null;
            const timingSuffix = lastRunMs !== null ? ` · ${lastRunMs} ms` : '';
            const statusLabel = runtimeStatus === 'completed'
              ? `Completed${timingSuffix}`
              : runtimeStatus === 'running'
                ? 'Running'
                : runtimeStatus === 'faulted'
                  ? `Failed${timingSuffix}`
                  : `Not started${timingSuffix}`;
            const statusIcon = runtimeStatus === 'completed' ? '✓' : runtimeStatus === 'running' ? '●' : runtimeStatus === 'faulted' ? '!' : '○';
            return (
              <li className={`pipeline-step pipeline-step--configuration ${runtimeStatus ? `pipeline-step--${runtimeStatus}` : ''}`} key={step.id} aria-label={`${step.displayName}, ${statusLabel}`}>
                <span className="pipeline-step__index">{String(index + 1).padStart(2, '0')}</span>
                <span><strong>{step.displayName}</strong><small><span aria-hidden="true">{statusIcon}</span> {statusLabel}</small></span>
                <code>{step.algorithmId}</code>
              </li>
            );
          })}
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

function InspectionPreview({ accessToken, run, nodeId }: { accessToken: string; run: InspectionRun | null; nodeId?: string }) {
  const [objectUrl, setObjectUrl] = useState('');
  const [previewError, setPreviewError] = useState('');

  useEffect(() => {
    let isCancelled = false;
    let nextObjectUrl = '';
    setObjectUrl('');
    setPreviewError('');
    if (!run || run.status !== 'completed') return () => undefined;
    void readInspectionPreview(accessToken, run.id, nodeId)
      .then((blob) => {
        if (isCancelled) return;
        nextObjectUrl = URL.createObjectURL(blob);
        setObjectUrl(nextObjectUrl);
      })
      .catch((loadError) => {
        if (!isCancelled) setPreviewError(loadError instanceof Error ? loadError.message : 'Workflow preview is unavailable.');
      });
    return () => {
      isCancelled = true;
      if (nextObjectUrl) URL.revokeObjectURL(nextObjectUrl);
    };
  }, [accessToken, nodeId, run?.id, run?.status]);

  if (objectUrl) {
    return <div className="pcb-visual pcb-visual--optical"><img className="pcb-visual__image" src={objectUrl} alt={`Workflow output for ${run?.boardSerial ?? 'inspection'}`} /></div>;
  }
  return (
    <div className="pcb-visual pcb-visual--optical" role="status">
      <span className="pcb-visual__placeholder">{previewError || (run ? `Preview ${formatRuntimeStep(run.status)}` : 'Run workflow to generate 2D evidence')}</span>
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