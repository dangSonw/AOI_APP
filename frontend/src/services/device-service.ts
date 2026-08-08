import type {
  CameraConfiguration,
  DeviceOverview,
  DeviceSnapshot,
  MotionConfiguration,
  MotionState,
  Position,
} from '../types/devices';
import { apiBlobRequest, apiRequest } from './api-client';

const commandId = (prefix: string) => `${prefix}-${Date.now()}-${crypto.randomUUID().slice(0, 8)}`;

export async function readDeviceSnapshot(accessToken: string): Promise<DeviceSnapshot> {
  const devices = await apiRequest<DeviceOverview>('/api/devices', {}, accessToken);
  let cameraConfiguration: CameraConfiguration | null = null;
  let motionConfiguration: MotionConfiguration | null = null;
  let motionState: MotionState | null = null;

  if (devices.camera.status === 'ready') {
    cameraConfiguration = await apiRequest<CameraConfiguration>(
      '/api/camera/configuration',
      {},
      accessToken,
    );
  }

  if (devices.motion.status === 'ready') {
    [motionConfiguration, motionState] = await Promise.all([
      apiRequest<MotionConfiguration>('/api/motion/configuration', {}, accessToken),
      apiRequest<MotionState>('/api/motion/state', {}, accessToken),
    ]);
  }

  return { devices, cameraConfiguration, motionConfiguration, motionState };
}

export function saveCameraConfiguration(accessToken: string, configuration: CameraConfiguration): Promise<CameraConfiguration> {
  return apiRequest('/api/camera/configuration', { method: 'PUT', body: JSON.stringify(configuration) }, accessToken);
}

export function saveMotionConfiguration(accessToken: string, configuration: MotionConfiguration): Promise<MotionConfiguration> {
  return apiRequest('/api/motion/configuration', { method: 'PUT', body: JSON.stringify(configuration) }, accessToken);
}

export function readCameraPreview(accessToken: string): Promise<Blob> {
  return apiBlobRequest('/api/camera/preview', accessToken);
}

export function homeMotion(accessToken: string): Promise<unknown> {
  return apiRequest('/api/motion/commands/home', { method: 'POST', body: JSON.stringify({ commandId: commandId('home') }) }, accessToken);
}

export function moveMotion(accessToken: string, target: Position, configuration: MotionConfiguration): Promise<unknown> {
  return apiRequest('/api/motion/commands/move-absolute', {
    method: 'POST',
    body: JSON.stringify({
      commandId: commandId('move'), target,
      maximumVelocityMillimetersPerSecond: configuration.maximumVelocityMillimetersPerSecond,
      maximumAccelerationMillimetersPerSecondSquared: configuration.maximumAccelerationMillimetersPerSecondSquared,
      settleMilliseconds: configuration.settleMilliseconds,
    }),
  }, accessToken);
}

export function stopMotion(accessToken: string): Promise<unknown> {
  return apiRequest('/api/motion/commands/stop', { method: 'POST', body: JSON.stringify({ commandId: commandId('stop') }) }, accessToken);
}

export function clearMotionFault(accessToken: string): Promise<unknown> {
  return apiRequest('/api/motion/commands/clear-fault', { method: 'POST', body: JSON.stringify({ commandId: commandId('clear') }) }, accessToken);
}