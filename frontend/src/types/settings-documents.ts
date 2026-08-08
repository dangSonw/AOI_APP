import type { CameraConfiguration, MotionConfiguration } from './devices';

export interface WorkstationProfile {
  stationDisplayName: string;
  deploymentMode: 'research' | 'simulation' | 'hardware-pilot' | 'production';
  cameraProfileName: string;
  camera: CameraConfiguration | null;
  motionProfileName: string;
  motion: MotionConfiguration | null;
  calibration: {
    calibrationId: string | null;
    artifactSha256: string | null;
    validUntil: string | null;
    blockProductionWhenInvalid: boolean;
  };
  poseToleranceMillimeters: number;
  triggerTimeoutMilliseconds: number;
}

export interface RecipeDefaults {
  activeRecipeSlug: string;
  serialRequired: boolean;
  lotRequired: boolean;
  runTimeoutSeconds: number;
  maximumRetries: number;
  decisionPolicy: 'strict' | 'review-borderline' | 'research';
  evidenceRequired: boolean;
  resultExportFormat: 'json' | 'csv' | 'ipc-cfx';
  defectTaxonomy: string;
}

export interface SystemPolicy {
  compute: {
    executionTarget: 'cpu' | 'cuda' | 'jetson' | 'remote-worker';
    maximumConcurrentInspections: number;
    maximumResearchJobs: number;
    memoryLimitMegabytes: number;
    gpuMemoryLimitMegabytes: number;
    deterministicExecution: boolean;
    randomSeed: number;
  };
  research: {
    artifactStoragePolicy: 'filesystem' | 'object-storage';
    trackingBackend: 'internal' | 'mlflow';
    registryBackend: 'internal' | 'mlflow';
    checkpointRetentionCount: number;
    productionAlias: 'champion';
    requireValidationEvidence: boolean;
  };
  retention: {
    previewDays: number;
    rawCaptureDays: number;
    resultEvidenceDays: number;
    auditDays: number;
    storageQuotaGigabytes: number;
    diskPressurePercent: number;
    legalHold: boolean;
  };
  integrations: {
    plcEnabled: boolean;
    mesEnabled: boolean;
    mesEndpoint: string;
    mesSecretReference: string | null;
    ipcCfxEnabled: boolean;
    opcUaEnabled: boolean;
    timeSyncRequired: boolean;
  };
  notifications: {
    machineFaults: boolean;
    adapterDegradation: boolean;
    calibrationExpiry: boolean;
    storagePressure: boolean;
    researchJobs: boolean;
    modelDrift: boolean;
    minimumIntervalSeconds: number;
  };
  securityUpdates: {
    sessionMinutes: number;
    auditExportEnabled: boolean;
    signedUpdatesRequired: boolean;
    updateChannel: 'stable' | 'pilot' | 'disabled';
    maintenanceWindow: string;
  };
}

export const DEFAULT_WORKSTATION_PROFILE: WorkstationProfile = {
  stationDisplayName: 'AOI Station 01', deploymentMode: 'simulation',
  cameraProfileName: 'Default camera', camera: null,
  motionProfileName: 'Default motion', motion: null,
  calibration: { calibrationId: null, artifactSha256: null, validUntil: null, blockProductionWhenInvalid: true },
  poseToleranceMillimeters: 0.05, triggerTimeoutMilliseconds: 5000,
};

export const DEFAULT_RECIPE_DEFAULTS: RecipeDefaults = {
  activeRecipeSlug: 'rev-c-mainboard', serialRequired: true, lotRequired: true,
  runTimeoutSeconds: 120, maximumRetries: 1, decisionPolicy: 'review-borderline',
  evidenceRequired: true, resultExportFormat: 'json', defectTaxonomy: 'ipc-a-610',
};

export const DEFAULT_SYSTEM_POLICY: SystemPolicy = {
  compute: { executionTarget: 'cpu', maximumConcurrentInspections: 1, maximumResearchJobs: 1, memoryLimitMegabytes: 4096, gpuMemoryLimitMegabytes: 0, deterministicExecution: true, randomSeed: 42 },
  research: { artifactStoragePolicy: 'filesystem', trackingBackend: 'internal', registryBackend: 'internal', checkpointRetentionCount: 5, productionAlias: 'champion', requireValidationEvidence: true },
  retention: { previewDays: 7, rawCaptureDays: 30, resultEvidenceDays: 365, auditDays: 2555, storageQuotaGigabytes: 500, diskPressurePercent: 85, legalHold: false },
  integrations: { plcEnabled: false, mesEnabled: false, mesEndpoint: '', mesSecretReference: null, ipcCfxEnabled: false, opcUaEnabled: false, timeSyncRequired: true },
  notifications: { machineFaults: true, adapterDegradation: true, calibrationExpiry: true, storagePressure: true, researchJobs: false, modelDrift: true, minimumIntervalSeconds: 60 },
  securityUpdates: { sessionMinutes: 480, auditExportEnabled: true, signedUpdatesRequired: true, updateChannel: 'stable', maintenanceWindow: 'Sunday 02:00-04:00' },
};