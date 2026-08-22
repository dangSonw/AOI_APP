export interface ResearchRun {
  id: string;
  experimentId: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  executionTarget: string;
  codeRevision: string;
  nodeVersions: Record<string, string>;
  environment: Record<string, unknown>;
  randomSeeds: Record<string, number>;
  resources: Record<string, unknown>;
  datasetVersions: Record<string, string>;
  parameters: Record<string, unknown>;
  metrics: Record<string, number>;
  outputArtifacts: Record<string, string>;
  error: string | null;
  createdAt: string;
}

export interface ModelCompatibility {
  task?: string;
  inputSchema?: string;
  outputSchema?: string;
  framework?: string;
  status?: string;
}

export interface DeepLearningTensorSpec {
  name: string;
  dtype: 'float32' | 'float16' | 'int64' | 'int32' | 'uint8' | 'bool';
  shape: Array<number | string>;
}

export interface DeepLearningArtifactContract {
  format: 'onnx';
  runtime: 'onnxruntime';
  runtimeVersion: string;
  inputSchema: DeepLearningTensorSpec[];
  outputSchema: DeepLearningTensorSpec[];
  preprocessing: Record<string, unknown>;
  postprocessing: Record<string, unknown>;
}

export interface RegisteredModelVersion {
  version: number;
  runId: string;
  artifactSha256: string;
  artifactVerified: boolean;
  validationEvidence: Record<string, unknown>;
  compatibility: ModelCompatibility;
  deepLearningContract?: DeepLearningArtifactContract;
}

export interface RegisteredModel {
  name: string;
  description: string;
  aliases: Record<string, number>;
  versions: RegisteredModelVersion[];
}

export type ModelAlias = 'candidate' | 'champion' | 'rollback';
export type ModelLifecycleAction = 'promote' | 'rollback';

export interface ModelPromotionEvent {
  id: number;
  action: ModelLifecycleAction;
  alias: ModelAlias;
  previousVersion: number | null;
  nextVersion: number;
  reason: string;
}
