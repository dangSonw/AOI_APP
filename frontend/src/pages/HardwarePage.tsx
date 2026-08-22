import { useEffect, useState } from 'react';
import { StatusBadge } from '../components/StatusBadge';
import {
  clearMotionFault,
  homeMotion,
  moveMotion,
  readCameraPreview,
  saveCameraConfiguration,
  saveMotionConfiguration,
  stopMotion,
} from '../services/device-service';
import type { CameraConfiguration, DeviceSnapshot, MotionConfiguration, Position } from '../types/devices';

interface HardwarePageProps {
  accessToken: string;
  snapshot: DeviceSnapshot | null;
  error: string;
  isLoading: boolean;
  onRefresh: () => Promise<void>;
}

export function HardwarePage({ accessToken, snapshot, error, isLoading, onRefresh }: HardwarePageProps) {
  const [cameraDraft, setCameraDraft] = useState<CameraConfiguration | null>(snapshot?.cameraConfiguration ?? null);
  const [motionDraft, setMotionDraft] = useState<MotionConfiguration | null>(snapshot?.motionConfiguration ?? null);
  const [target, setTarget] = useState<Position>(snapshot?.motionState?.position ?? { xMillimeters: 0, yMillimeters: 0, zMillimeters: 0 });
  const [previewUrl, setPreviewUrl] = useState('');
  const [message, setMessage] = useState('');
  const [isCameraDirty, setIsCameraDirty] = useState(false);
  const [isMotionDirty, setIsMotionDirty] = useState(false);

  useEffect(() => {
    if (snapshot) {
      if (!isCameraDirty) setCameraDraft(snapshot.cameraConfiguration);
      if (!isMotionDirty) setMotionDraft(snapshot.motionConfiguration);
      if (snapshot.motionState) setTarget(snapshot.motionState.position);
    }
  }, [isCameraDirty, isMotionDirty, snapshot]);

  useEffect(() => {
    if (!snapshot || snapshot.devices.camera.status !== 'ready') return;
    let objectUrl = '';
    void readCameraPreview(accessToken).then((blob) => {
      objectUrl = URL.createObjectURL(blob);
      setPreviewUrl(objectUrl);
    }).catch(() => undefined);
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [accessToken, snapshot?.devices.camera.checkedAt]);

  const run = async (action: () => Promise<unknown>, successMessage: string) => {
    setMessage('');
    await action();
    setMessage(successMessage);
    await onRefresh();
  };

  if (!snapshot) {
    return <div className="hardware-page"><header className="workspace-title-row"><div><h1>Hardware</h1></div></header><p className="studio-message studio-message--error" role="alert">{error || (isLoading ? 'Reading device adapters…' : 'Device state is unavailable.')}</p></div>;
  }

  const camera = snapshot.devices.camera;
  const motion = snapshot.devices.motion;
  const motionState = snapshot.motionState;
  const modeLabel = camera.mode === 'simulation' ? 'Simulation adapter' : 'Hardware adapter';

  return (
    <div className="hardware-page" aria-busy={isLoading}>
      <header className="workspace-title-row">
        <div><h1>Hardware</h1></div>
        <StatusBadge status={camera.status === 'ready' && motion.status === 'ready' ? 'success' : 'warning'} label={modeLabel} />
      </header>

      <section className="hardware-signal-rail" aria-label="Device signal route">
        <span><strong>Camera · 9101</strong><small>{camera.implementation}</small></span><i>→</i>
        <span><strong>Backend · 8000</strong><small>Authenticated gateway</small></span><i>→</i>
        <span><strong>AOI Studio</strong><small>Configuration and state</small></span><i>↔</i>
        <span><strong>MCU · 9102</strong><small>{motion.implementation}</small></span>
      </section>

      {error && <p className="studio-message studio-message--error" role="alert">{error}</p>}
      {message && <p className="studio-message studio-message--success" role="status">{message}</p>}

      <div className="hardware-grid">
        <section className="hardware-device-panel">
          <header><div><span className="overline">Camera signal</span><h2>{camera.implementation}</h2></div><StatusBadge status={camera.status === 'ready' ? 'success' : 'warning'} label={camera.status} /></header>
          <div className="hardware-preview">
            {previewUrl ? <img src={previewUrl} alt="Current camera adapter preview" /> : <span>Preview is waiting for a ready camera adapter.</span>}
            <footer><span>{camera.mode}</span><code>Protocol {camera.protocolVersion}</code></footer>
          </div>
          {camera.status !== 'ready' && <p className="hardware-diagnostic">{camera.detail ?? 'Camera adapter configuration is unavailable.'}</p>}
          {cameraDraft && <div className="hardware-form-grid">
            <label>Camera ID<input value={cameraDraft.cameraId} onChange={(event) => { setIsCameraDirty(true); setCameraDraft({ ...cameraDraft, cameraId: event.target.value }); }} /></label>
            <label>Sensor mode<input value={cameraDraft.sensorMode} onChange={(event) => { setIsCameraDirty(true); setCameraDraft({ ...cameraDraft, sensorMode: event.target.value }); }} /></label>
            <label>Exposure <span><input type="number" min="1" max="10000000" value={cameraDraft.exposureMicroseconds} onChange={(event) => { setIsCameraDirty(true); setCameraDraft({ ...cameraDraft, exposureMicroseconds: Number(event.target.value) }); }} /> µs</span></label>
            <label>Analog gain <span><input type="number" min="0.1" max="256" step="0.1" value={cameraDraft.analogGain} onChange={(event) => { setIsCameraDirty(true); setCameraDraft({ ...cameraDraft, analogGain: Number(event.target.value) }); }} /> ×</span></label>
          </div>}
          <button className="studio-primary-button" type="button" disabled={!cameraDraft || camera.status !== 'ready'} onClick={() => cameraDraft && void run(async () => { await saveCameraConfiguration(accessToken, cameraDraft); setIsCameraDirty(false); }, 'Camera configuration applied to the active adapter.').catch((saveError) => setMessage(saveError instanceof Error ? saveError.message : 'Camera configuration failed.'))}>Apply camera configuration</button>
        </section>

        <section className="hardware-device-panel">
          <header><div><span className="overline">Motion controller</span><h2>{motionState ? motionState.state.replace(/-/g, ' ') : motion.implementation}</h2></div><StatusBadge status={motionState?.fault || motionState?.emergencyStop ? 'error' : motion.status === 'ready' ? 'success' : 'warning'} label={motionState ? (motionState.isHomed ? 'Homed' : 'Not homed') : motion.status} /></header>
          {motionState ? <>
          <div className="hardware-coordinate-readout"><span>X <strong>{motionState.position.xMillimeters.toFixed(3)}</strong></span><span>Y <strong>{motionState.position.yMillimeters.toFixed(3)}</strong></span><span>Z <strong>{motionState.position.zMillimeters.toFixed(3)}</strong></span><small>millimetres · revision {motionState.revision}</small></div>
          <div className="hardware-interlocks"><span>{motionState.doorClosed ? '✓ Door closed' : '⚠ Door open'}</span><span>{motionState.communicationConnected ? '✓ MCU connected' : '⚠ MCU disconnected'}</span><span>{motionState.emergencyStop ? '⛔ Emergency stop' : '✓ E-stop released'}</span></div>
          </> : <p className="hardware-diagnostic">{motion.detail ?? 'Motion adapter state is unavailable.'}</p>}
          {motionDraft && <div className="hardware-form-grid">
            <label>Max velocity <span><input type="number" min="0.1" value={motionDraft.maximumVelocityMillimetersPerSecond} onChange={(event) => { setIsMotionDirty(true); setMotionDraft({ ...motionDraft, maximumVelocityMillimetersPerSecond: Number(event.target.value) }); }} /> mm/s</span></label>
            <label>Max acceleration <span><input type="number" min="0.1" value={motionDraft.maximumAccelerationMillimetersPerSecondSquared} onChange={(event) => { setIsMotionDirty(true); setMotionDraft({ ...motionDraft, maximumAccelerationMillimetersPerSecondSquared: Number(event.target.value) }); }} /> mm/s²</span></label>
            <label>Settle time <span><input type="number" min="0" value={motionDraft.settleMilliseconds} onChange={(event) => { setIsMotionDirty(true); setMotionDraft({ ...motionDraft, settleMilliseconds: Number(event.target.value) }); }} /> ms</span></label>
          </div>}
          <div className="hardware-target-grid">
            {(['xMillimeters', 'yMillimeters', 'zMillimeters'] as const).map((axis) => <label key={axis}>{axis[0].toUpperCase()} target<input type="number" value={target[axis]} onChange={(event) => setTarget({ ...target, [axis]: Number(event.target.value) })} /></label>)}
          </div>
          <div className="hardware-actions">
            <button className="studio-primary-button" type="button" disabled={motion.status !== 'ready'} onClick={() => void run(() => homeMotion(accessToken), 'Motion controller homed.').catch((actionError) => setMessage(actionError instanceof Error ? actionError.message : 'Home failed.'))}>Home</button>
            <button className="studio-secondary-button" type="button" disabled={!motionDraft || !motionState?.isHomed} onClick={() => motionDraft && void run(() => moveMotion(accessToken, target, motionDraft), 'Absolute move completed.').catch((actionError) => setMessage(actionError instanceof Error ? actionError.message : 'Move failed.'))}>Move absolute</button>
            <button className="studio-secondary-button" type="button" disabled={motion.status !== 'ready'} onClick={() => void run(() => stopMotion(accessToken), 'Stop command completed.').catch((actionError) => setMessage(actionError instanceof Error ? actionError.message : 'Stop failed.'))}>Stop</button>
            <button className="studio-secondary-button" type="button" disabled={motion.status !== 'ready'} onClick={() => void run(() => clearMotionFault(accessToken), 'Motion fault cleared.').catch((actionError) => setMessage(actionError instanceof Error ? actionError.message : 'Clear fault failed.'))}>Clear fault</button>
          </div>
          <button className="studio-secondary-button" type="button" disabled={!motionDraft || motion.status !== 'ready'} onClick={() => motionDraft && void run(async () => { await saveMotionConfiguration(accessToken, motionDraft); setIsMotionDirty(false); }, 'Motion profile applied to the active adapter.').catch((saveError) => setMessage(saveError instanceof Error ? saveError.message : 'Motion configuration failed.'))}>Apply motion profile</button>
        </section>
      </div>
    </div>
  );
}