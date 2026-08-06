export type DeviceMode = 'hardware' | 'simulation';
export type DeviceStatus = 'ready' | 'degraded' | 'unavailable';

export interface DeviceHealth {
  service: string;
  implementation: string;
  mode: DeviceMode;
  status: DeviceStatus;
  protocolVersion: string;
  checkedAt: string;
  detail?: string | null;
}

export interface DeviceOverview {
  camera: DeviceHealth;
  motion: DeviceHealth;
}

export interface CameraConfiguration {
  cameraId: string;
  sensorMode: string;
  exposureMicroseconds: number;
  analogGain: number;
}

export interface MotionConfiguration {
  maximumVelocityMillimetersPerSecond: number;
  maximumAccelerationMillimetersPerSecondSquared: number;
  settleMilliseconds: number;
}

export interface Position {
  xMillimeters: number;
  yMillimeters: number;
  zMillimeters: number;
}

export interface MotionState {
  revision: number;
  state: 'boot' | 'not-homed' | 'homing' | 'idle' | 'moving' | 'stopping' | 'fault' | 'emergency-stop';
  isHomed: boolean;
  isInPosition: boolean;
  position: Position;
  activeCommandId?: string | null;
  emergencyStop: boolean;
  doorClosed: boolean;
  communicationConnected: boolean;
  fault?: string | null;
  updatedAt: string;
}

export interface DeviceSnapshot {
  devices: DeviceOverview;
  cameraConfiguration: CameraConfiguration | null;
  motionConfiguration: MotionConfiguration | null;
  motionState: MotionState | null;
}