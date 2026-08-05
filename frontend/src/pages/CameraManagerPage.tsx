import { useState } from 'react';
import { StatusBadge } from '../components/StatusBadge';

const LIGHT_VIEWS = [
  { id: 1, direction: 'North', exposure: '8.0 ms', intensity: 82 },
  { id: 2, direction: 'East', exposure: '8.0 ms', intensity: 74 },
  { id: 3, direction: 'South', exposure: '8.0 ms', intensity: 88 },
  { id: 4, direction: 'West', exposure: '8.0 ms', intensity: 79 },
];

export function CameraManagerPage() {
  const [selectedView, setSelectedView] = useState(1);
  const [intensity, setIntensity] = useState(82);
  const [isApplying, setIsApplying] = useState(false);
  const [message, setMessage] = useState('');

  const handleApply = () => {
    setIsApplying(true);
    setMessage('');
    window.setTimeout(() => {
      setIsApplying(false);
      setMessage('Calibration configuration applied.');
    }, 450);
  };

  return (
    <div className="camera-page">
      <header className="workspace-title-row">
        <div>
          <span className="overline">Camera manager</span>
          <h1>Multi-view photometric stereo</h1>
          <p>Configure synchronized light views, validate calibration, and inspect reconstructed surface depth.</p>
        </div>
        <StatusBadge status="success" label="Calibration valid" />
      </header>

      <section className="camera-workspace">
        <div className="camera-captures">
          <header className="section-heading">
            <div><span className="overline">Capture set</span><h2>Synchronized light captures</h2></div>
            <span>4 / 4 views valid</span>
          </header>
          <div className="capture-grid">
            {LIGHT_VIEWS.map((view) => (
              <button
                type="button"
                key={view.id}
                className={`capture-card ${selectedView === view.id ? 'capture-card--selected' : ''}`}
                onClick={() => {
                  setSelectedView(view.id);
                  setIntensity(view.intensity);
                }}
              >
                <span className={`capture-card__preview capture-card__preview--${view.id}`}>
                  <span className="capture-card__board" />
                  <span className="capture-card__light" aria-hidden="true">{view.direction.slice(0, 1)}</span>
                </span>
                <span className="capture-card__meta">
                  <strong>Light view {view.id}</strong>
                  <span>{view.direction} · {view.exposure}</span>
                </span>
                <StatusBadge status="success" label="Valid" />
              </button>
            ))}
          </div>
          <article className="surface-viewer">
            <header><strong>Reconstructed surface depth</strong><span>Selected view {selectedView}</span></header>
            <div className="surface-viewer__canvas" role="img" aria-label="Simulated reconstructed PCB surface depth">
              <span className="surface-mesh" />
              <span className="surface-chip surface-chip--one" />
              <span className="surface-chip surface-chip--two" />
              <span className="surface-chip surface-chip--three" />
              <span className="surface-viewer__axis">Z<br />↑<br /><small>X →</small></span>
            </div>
          </article>
        </div>

        <aside className="camera-inspector">
          <div className="panel-heading"><span>Capture configuration</span><span>Rig 01</span></div>
          <section>
            <span className="overline">Light rig</span>
            <strong>Ring-4 · synchronized</strong>
            <p>25° elevation · Cross polarization</p>
          </section>
          <label className="range-control">
            <span><strong>Intensity balance</strong><output>{intensity}%</output></span>
            <input type="range" min="40" max="100" value={intensity} onChange={(event) => setIntensity(Number(event.target.value))} />
          </label>
          <dl className="property-list">
            <div><dt>Exposure lock</dt><dd>8.0 ms</dd></div>
            <div><dt>Polarization</dt><dd>Cross</dd></div>
            <div><dt>Trigger delay</dt><dd>0.24 ms</dd></div>
            <div><dt>Camera gain</dt><dd>1.2 dB</dd></div>
          </dl>
          <section className="quality-panel">
            <span className="overline">Reconstruction quality</span>
            <dl>
              <div><dt>Surface coverage</dt><dd>99.2%</dd></div>
              <div><dt>Normal RMSE</dt><dd>0.18°</dd></div>
              <div><dt>Height repeatability</dt><dd>± 4.1 μm</dd></div>
            </dl>
          </section>
          {message && <p className="studio-message studio-message--success" role="status">{message}</p>}
          <button className="studio-primary-button" type="button" disabled={isApplying} onClick={handleApply}>
            {isApplying ? 'Applying…' : 'Recalibrate & apply'}
          </button>
        </aside>
      </section>
    </div>
  );
}