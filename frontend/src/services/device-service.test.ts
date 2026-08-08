import { afterEach, describe, expect, it, vi } from 'vitest';
import { readCameraPreview, readDeviceSnapshot, saveCameraConfiguration } from './device-service';

afterEach(() => vi.unstubAllGlobals());

describe('device service', () => {
  it('reads synchronized camera and motion state through the authenticated backend', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ camera: { status: 'ready' }, motion: { status: 'ready' } }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ cameraId: 'top-camera', sensorMode: '3280x2464', exposureMicroseconds: 8000, analogGain: 1 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ maximumVelocityMillimetersPerSecond: 20, maximumAccelerationMillimetersPerSecondSquared: 40, settleMilliseconds: 250 }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ state: 'idle', position: { xMillimeters: 1, yMillimeters: 2, zMillimeters: 3 } }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const snapshot = await readDeviceSnapshot('token');

    expect(snapshot.cameraConfiguration?.exposureMicroseconds).toBe(8000);
    expect(snapshot.motionState?.position.xMillimeters).toBe(1);
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  it('writes camera settings only through the backend gateway', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ cameraId: 'top-camera' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await saveCameraConfiguration('token', {
      cameraId: 'top-camera', sensorMode: '3280x2464', exposureMicroseconds: 9000, analogGain: 2,
    });

    expect(fetchMock.mock.calls[0][0]).toContain('/api/camera/configuration');
    expect(fetchMock.mock.calls[0][1]?.method).toBe('PUT');
  });

  it('returns hardware diagnostics without calling operational endpoints when adapters are unavailable', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      camera: { service: 'camera', implementation: 'jetson-csi-camera', mode: 'hardware', status: 'unavailable', protocolVersion: '1.0', checkedAt: '2026-08-06T00:00:00Z', detail: 'CSI camera is not connected.' },
      motion: { service: 'motion', implementation: 'uart-motion-controller', mode: 'hardware', status: 'unavailable', protocolVersion: '1.0', checkedAt: '2026-08-06T00:00:00Z', detail: 'MCU UART is not connected.' },
    }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const snapshot = await readDeviceSnapshot('token');

    expect(snapshot.devices.camera.mode).toBe('hardware');
    expect(snapshot.cameraConfiguration).toBeNull();
    expect(snapshot.motionState).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('keeps camera configuration when motion is unavailable', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({
        camera: { status: 'ready' },
        motion: { status: 'unavailable' },
      }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        cameraId: 'top-camera',
        sensorMode: '3280x2464',
        exposureMicroseconds: 8000,
        analogGain: 1,
      }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const snapshot = await readDeviceSnapshot('token');

    expect(snapshot.cameraConfiguration?.cameraId).toBe('top-camera');
    expect(snapshot.motionConfiguration).toBeNull();
    expect(snapshot.motionState).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('keeps motion configuration and state when camera is unavailable', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({
        camera: { status: 'unavailable' },
        motion: { status: 'ready' },
      }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        maximumVelocityMillimetersPerSecond: 20,
        maximumAccelerationMillimetersPerSecondSquared: 40,
        settleMilliseconds: 250,
      }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        state: 'idle',
        position: { xMillimeters: 1, yMillimeters: 2, zMillimeters: 3 },
      }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const snapshot = await readDeviceSnapshot('token');

    expect(snapshot.cameraConfiguration).toBeNull();
    expect(snapshot.motionConfiguration?.settleMilliseconds).toBe(250);
    expect(snapshot.motionState?.position.zMillimeters).toBe(3);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('always reloads camera preview bytes instead of reusing a cached test pattern', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(new Blob(['webcam-frame'], { type: 'image/png' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await readCameraPreview('token');

    expect(fetchMock.mock.calls[0][1]?.cache).toBe('no-store');
  });
});