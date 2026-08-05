import type { PhysicalInputState, PhysicalOutputState } from '../types/physical-io';
import type { InspectionStatus } from '../types/workspace';
import { StatusBadge } from '../components/StatusBadge';

interface DashboardPageProps {
  inputs: PhysicalInputState | null;
  outputs: PhysicalOutputState | null;
  isLoading: boolean;
  error: string;
  isRunning: boolean;
  onOutputToggle: (signalName: string, currentValue: boolean) => void;
}

const METRICS = [
  { label: 'First-pass yield', value: '99.1', unit: '%', delta: '+0.4%' },
  { label: 'Cycle time', value: '0.42', unit: 's', delta: '-18 ms' },
  { label: 'Queue', value: '54', unit: 'boards', delta: '12 min' },
  { label: 'Inspected', value: '1,247', unit: 'today', delta: '+5.2%' },
  { label: 'Defects', value: '12', unit: 'flagged', delta: '0.96%' },
];

const PIPELINE_STEPS: Array<{ label: string; runtime: string; status: InspectionStatus }> = [
  { label: 'Camera', runtime: '12 ms', status: 'success' },
  { label: 'Measure', runtime: '3 ms', status: 'success' },
  { label: 'Depth', runtime: '18 ms', status: 'success' },
  { label: 'PatchCore', runtime: '21 ms', status: 'running' },
  { label: 'YOLO', runtime: '16 ms', status: 'idle' },
  { label: 'Decision', runtime: '8 ms', status: 'idle' },
];

export function DashboardPage({ inputs, outputs, isLoading, error, isRunning, onOutputToggle }: DashboardPageProps) {
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

  return (
    <div className="dashboard-layout" aria-busy={isLoading}>
      <div className="dashboard-main">
        <header className="workspace-title-row">
          <div>
            <span className="overline">Mission control</span>
            <h1>Inspection workspace</h1>
            <p>Live production state, optical views, and pipeline health.</p>
          </div>
          <StatusBadge status={lineStatus} label={lineStatusLabel} />
        </header>

        {error && <p className="studio-message studio-message--error" role="alert">{error}</p>}

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
        </div>

        <section className="viewer-grid" aria-label="Inspection viewers">
          <article className="inspection-viewer">
            <header><strong>2D optical view</strong><StatusBadge status="success" label="Live" /></header>
            <div className="pcb-visual pcb-visual--optical" role="img" aria-label="Simulated top-down PCB optical inspection">
              <span className="pcb-visual__board" />
              <span className="pcb-visual__roi pcb-visual__roi--one">ROI 03</span>
              <span className="pcb-visual__roi pcb-visual__roi--two">ROI 07</span>
              <span className="viewer-reticle" aria-hidden="true">+</span>
            </div>
            <footer><span>Top camera · 12 MP</span><span>8.0 ms · Gain 1.2</span></footer>
          </article>

          <article className="inspection-viewer">
            <header><strong>3D component heightmap</strong><StatusBadge status="success" label="Synced" /></header>
            <div className="pcb-visual pcb-visual--depth" role="img" aria-label="Simulated PCB component depth map">
              <span className="depth-plane" />
              <span className="depth-component depth-component--one" />
              <span className="depth-component depth-component--two" />
              <span className="depth-component depth-component--three" />
              <span className="depth-scale">0 μm<span />2400 μm</span>
            </div>
            <footer><span>Photometric stereo</span><span>RMSE 0.18°</span></footer>
          </article>
        </section>

        <section className="io-console">
          <header>
            <div><span className="overline">Physical I/O</span><strong>Machine interface</strong></div>
            <span>Revision {outputs?.revision ?? inputs?.revision ?? '—'}</span>
          </header>
          <div className="io-console__signals">
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
          </div>
        </section>
      </div>

      <aside className="pipeline-panel" aria-label="Inspection flow">
        <div className="panel-heading"><span>Inspection flow</span><span>v2.14</span></div>
        <ol className="pipeline-list">
          {PIPELINE_STEPS.map((step, index) => (
            <li className={`pipeline-step pipeline-step--${step.status}`} key={step.label}>
              <span className="pipeline-step__index">{String(index + 1).padStart(2, '0')}</span>
              <span><strong>{step.label}</strong><small>{step.status}</small></span>
              <time>{step.runtime}</time>
            </li>
          ))}
        </ol>
        <section className="pipeline-summary">
          <span className="overline">Last decision</span>
          <strong>PASS</strong>
          <span>PCB-24-08192 · 98.7% confidence</span>
        </section>
      </aside>
    </div>
  );
}

function formatSignalName(name: string): string {
  return name.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/^./, (character) => character.toUpperCase());
}