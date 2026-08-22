import { useEffect, useState } from 'react';
import { LightDirectionOverlay } from '../components/LightDirectionOverlay';
import { StatusBadge } from '../components/StatusBadge';
import type { PhotometricLight, WorkstationPreferences } from '../types/workstation-preferences';
import { resizePhotometricLights } from '../utils/workstation-preferences';

interface CameraManagerPageProps {
  preferences: WorkstationPreferences;
  onChange: (preferences: WorkstationPreferences) => void;
}

export function CameraManagerPage({ preferences, onChange }: CameraManagerPageProps) {
  const [selectedView, setSelectedView] = useState(1);
  const [message, setMessage] = useState('');
  const lights = preferences.photometric.lights;
  const selectedLight = lights.find((light) => light.id === selectedView) ?? lights[0];

  useEffect(() => {
    if (!lights.some((light) => light.id === selectedView)) setSelectedView(lights[0]?.id ?? 1);
  }, [lights, selectedView]);

  const updatePhotometric = (lightCount: number, nextLights: PhotometricLight[]) => onChange({
    ...preferences,
    photometric: { lightCount, lights: nextLights },
  });
  const updateSelectedLight = (patch: Partial<PhotometricLight>) => updatePhotometric(
    lights.length,
    lights.map((light) => light.id === selectedLight.id ? { ...light, ...patch } : light),
  );

  return (
    <div className="camera-page">
      <header className="workspace-title-row">
        <div>
          <h1>Camera rig</h1>
        </div>
        <StatusBadge status="success" label="Calibration valid" />
      </header>

      <section className="camera-workspace">
        <div className="camera-captures">
          <header className="section-heading">
            <div><span className="overline">Capture set</span><h2>Synchronized light captures</h2></div>
            <span>{lights.length} / {lights.length} views configured</span>
          </header>
          <div className="capture-grid">
            {lights.map((light) => (
              <button
                type="button"
                key={light.id}
                className={`capture-card ${selectedView === light.id ? 'capture-card--selected' : ''}`}
                onClick={() => setSelectedView(light.id)}
              >
                <span className="capture-card__preview">
                  <span className="capture-card__board" />
                  <LightDirectionOverlay light={light} />
                </span>
                <span className="capture-card__meta">
                  <strong>Light view {light.id}</strong>
                  <span>Azimuth {light.azimuth}° · Elevation {light.elevation}°</span>
                </span>
                <StatusBadge status="success" label="Configured" />
              </button>
            ))}
          </div>
          <article className="surface-viewer">
            <header><strong>Reconstructed surface depth</strong><span>Selected view {selectedLight.id}</span></header>
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
          <div className="panel-heading"><span>Capture configuration</span><span>Image count {lights.length}</span></div>
          <label className="camera-field"><span>Workstation ID</span><input value={preferences.workstationId} readOnly /></label>
          <label className="camera-field"><span>Number of lights and images</span><input type="number" min="1" max="64" value={lights.length} onChange={(event) => {
            const lightCount = Math.min(64, Math.max(1, Number(event.target.value) || 1));
            updatePhotometric(lightCount, resizePhotometricLights(lights, lightCount));
          }} /></label>
          <section><span className="overline">Selected light</span><strong>Light {selectedLight.id}</strong><p>Adjust the vector against the camera preview.</p></section>
          <label className="range-control"><span><strong>Azimuth</strong><output>{selectedLight.azimuth}°</output></span><input type="range" min="0" max="359" value={selectedLight.azimuth} onChange={(event) => updateSelectedLight({ azimuth: Number(event.target.value) })} /></label>
          <label className="range-control"><span><strong>Elevation</strong><output>{selectedLight.elevation}°</output></span><input type="range" min="0" max="90" value={selectedLight.elevation} onChange={(event) => updateSelectedLight({ elevation: Number(event.target.value) })} /></label>
          <label className="range-control"><span><strong>Intensity</strong><output>{selectedLight.intensity}%</output></span><input type="range" min="0" max="100" value={selectedLight.intensity} onChange={(event) => updateSelectedLight({ intensity: Number(event.target.value) })} /></label>
          <p className="camera-save-hint">Save this rig from the workspace preferences when the configuration is ready.</p>
          {message && <p className="studio-message studio-message--success" role="status">{message}</p>}
          <button className="studio-primary-button" type="button" onClick={() => setMessage('Photometric draft validated. Ready to save.')}>Validate configuration</button>
        </aside>
      </section>
    </div>
  );
}