import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { HardwarePage } from './HardwarePage';

describe('HardwarePage', () => {
  it('renders mode-aware camera and motion controls from a shared device snapshot', () => {
    const markup = renderToStaticMarkup(<HardwarePage
      accessToken="token"
      snapshot={{
        devices: {
          camera: { service: 'camera', implementation: 'replay-camera', mode: 'simulation', status: 'ready', protocolVersion: '1.0', checkedAt: '2026-08-06T00:00:00Z' },
          motion: { service: 'motion', implementation: 'virtual-motion-controller', mode: 'simulation', status: 'ready', protocolVersion: '1.0', checkedAt: '2026-08-06T00:00:00Z' },
        },
        cameraConfiguration: { cameraId: 'top-camera', sensorMode: '3280x2464', exposureMicroseconds: 8000, analogGain: 1 },
        motionConfiguration: { maximumVelocityMillimetersPerSecond: 20, maximumAccelerationMillimetersPerSecondSquared: 40, settleMilliseconds: 250 },
        motionState: { revision: 1, state: 'idle', isHomed: true, isInPosition: true, position: { xMillimeters: 1, yMillimeters: 2, zMillimeters: 3 }, emergencyStop: false, doorClosed: true, communicationConnected: true, fault: null, updatedAt: '2026-08-06T00:00:00Z' },
      }}
      error=""
      isLoading={false}
      onRefresh={async () => undefined}
    />);

    expect(markup).toContain('Hardware');
    expect(markup).toContain('Simulation adapter');
    expect(markup).toContain('Camera signal');
    expect(markup).toContain('Motion controller');
    expect(markup).toContain('8000');
  });

  it('renders actionable hardware diagnostics without operational controls crashing', () => {
    const markup = renderToStaticMarkup(<HardwarePage
      accessToken="token"
      snapshot={{
        devices: {
          camera: { service: 'camera', implementation: 'jetson-csi-camera', mode: 'hardware', status: 'unavailable', protocolVersion: '1.0', checkedAt: '2026-08-06T00:00:00Z', detail: 'CSI camera is not connected.' },
          motion: { service: 'motion', implementation: 'uart-motion-controller', mode: 'hardware', status: 'unavailable', protocolVersion: '1.0', checkedAt: '2026-08-06T00:00:00Z', detail: 'MCU UART is not connected.' },
        },
        cameraConfiguration: null,
        motionConfiguration: null,
        motionState: null,
      }}
      error=""
      isLoading={false}
      onRefresh={async () => undefined}
    />);

    expect(markup).toContain('Hardware adapter');
    expect(markup).toContain('CSI camera is not connected.');
    expect(markup).toContain('MCU UART is not connected.');
  });
});