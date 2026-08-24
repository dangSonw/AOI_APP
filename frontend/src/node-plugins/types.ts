import type { AlgorithmDefinition, ParameterValue, WorkflowNode } from '../types/workflow';
import type { TrainingJob, TrainingJobCreate } from '../types/training-job';

export interface NodePluginDatasetContext {
  listVersions: (datasetId: string) => Promise<readonly string[]>;
}

export interface NodePluginTrainingContext {
  create: (request: Omit<TrainingJobCreate, 'recipeSlug' | 'workflowRevision' | 'nodeInstanceId'>) => Promise<TrainingJob>;
  read: (runId: string) => Promise<TrainingJob>;
  cancel: (runId: string) => Promise<TrainingJob>;
  openRun: (runId: string) => void;
}

export interface NodePluginNavigationContext {
  openResearch: (query?: string) => void;
  openModels: (modelName?: string) => void;
}

export interface NodePluginPlatformContext {
  accessToken: string;
  recipeSlug: string;
  workflowRevision: number;
  nodeInstanceId: string;
  datasets?: NodePluginDatasetContext;
  training: NodePluginTrainingContext;
  navigation?: NodePluginNavigationContext;
}

export interface NodeInspectorPluginProps {
  node: WorkflowNode;
  definition: AlgorithmDefinition;
  updateParameter: (key: string, value: ParameterValue) => void;
  context?: NodePluginPlatformContext;
}

export type NodeInspectorPlugin = (props: NodeInspectorPluginProps) => JSX.Element;

export interface NodeResultPluginProps {
  node: WorkflowNode;
  definition: AlgorithmDefinition;
  result: Readonly<Record<string, unknown>>;
  context?: NodePluginPlatformContext;
}

export interface NodePreviewPluginProps {
  node: WorkflowNode;
  definition: AlgorithmDefinition;
  value: unknown;
}

export type NodeResultPlugin = (props: NodeResultPluginProps) => JSX.Element;
export type NodePreviewPlugin = (props: NodePreviewPluginProps) => JSX.Element;

export interface NodePluginDescriptor {
  nodeId: string;
  Inspector?: NodeInspectorPlugin;
  ResultView?: NodeResultPlugin;
  Preview?: NodePreviewPlugin;
}
