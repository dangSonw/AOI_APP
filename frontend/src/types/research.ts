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
