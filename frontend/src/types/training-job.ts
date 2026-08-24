export type TrainingJobStatus =
  | 'queued'
  | 'preparing-dataset'
  | 'validating'
  | 'training'
  | 'evaluating'
  | 'persisting-artifacts'
  | 'cancelling'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface TrainingDatasetBinding {
  datasetId: string;
  version: string;
}

export interface TrainingJobCreate {
  experimentId: string;
  recipeSlug: string;
  workflowRevision: number;
  nodeInstanceId: string;
  nodeId: string;
  nodePackageVersion: string;
  actionName: string;
  executionTarget: 'local-cpu' | 'local-gpu' | 'adapter';
  datasetBindings: Record<string, TrainingDatasetBinding>;
  parameters: Record<string, unknown>;
  randomSeeds: Record<string, number>;
  parentRunId: string | null;
}

export interface TrainingProgress {
  stage: TrainingJobStatus;
  processedUnits: number;
  totalUnits: number | null;
  fraction: number | null;
  message: string;
}

export interface TrainingArtifact {
  id: number;
  name: string;
  sha256: string;
  mediaType: string;
  byteLength: number;
}

export interface TrainingJob {
  id: string;
  experimentId: string;
  status: TrainingJobStatus;
  executionTarget: string;
  codeRevision: string;
  nodeId: string;
  nodeInstanceId: string;
  nodePackageVersion: string;
  actionName: string;
  workflowRevision: number;
  datasetBindings: Record<string, TrainingDatasetBinding>;
  parameters: Record<string, unknown>;
  randomSeeds: Record<string, number>;
  environment: Record<string, unknown>;
  progress: TrainingProgress | null;
  metrics: Record<string, number>;
  outputArtifacts: TrainingArtifact[];
  error: string | null;
  parentRunId: string | null;
  createdAt: string;
  completedAt: string | null;
}

export const TERMINAL_TRAINING_JOB_STATUSES: ReadonlySet<TrainingJobStatus> = new Set([
  'completed', 'failed', 'cancelled',
]);