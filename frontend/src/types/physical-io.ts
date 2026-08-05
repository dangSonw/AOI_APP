export interface PhysicalInputState {
  revision: number;
  updatedAt: string;
  machine: {
    emergencyStop: boolean;
    inspectionTrigger: boolean;
    doorClosed: boolean;
  };
  sensors: Record<string, boolean | number | string>;
}

export interface PhysicalOutputState {
  revision: number;
  updatedAt: string;
  signals: Record<string, boolean | number | string>;
}