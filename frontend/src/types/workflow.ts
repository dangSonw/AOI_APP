export type DataType =
  | 'generic'
  | 'boolean'
  | 'image'
  | 'image-set'
  | 'mask'
  | 'roi-set'
  | 'keypoints'
  | 'contours'
  | 'features'
  | 'detections'
  | 'anomaly-map'
  | 'score'
  | 'transform'
  | 'decision';

export type PortDirection = 'input' | 'output';
export type PortChannel = 'data' | 'control';
export type PortOrigin = 'system' | 'default' | 'custom';
export type RuntimeBindingMode = 'slot' | 'passthrough' | 'none';
export type ParameterKind = 'boolean' | 'integer' | 'number' | 'text' | 'select' | 'json' | 'reference' | 'model-reference';
export type ParameterValue = null | boolean | number | string | ParameterValue[] | { [key: string]: ParameterValue };
export type NodeUse = 'test' | 'debug' | 'release';

export interface PortDefinition {
  key: string;
  label: string;
  direction: PortDirection;
  dataType: DataType;
  required: boolean;
  variadic: boolean;
}

export interface ParameterDefinition {
  key: string;
  label: string;
  kind: ParameterKind;
  defaultValue: ParameterValue;
  required: boolean;
  minimum: number | null;
  maximum: number | null;
  options: ParameterValue[];
  description: string;
}

export interface AlgorithmDefinition {
  id: string;
  name: string;
  description: string;
  category: string;
  documentationGroup: string;
  availability: 'configuration-only';
  use: NodeUse;
  inputs: PortDefinition[];
  outputs: PortDefinition[];
  controlPorts?: PortDefinition[];
  parameters: ParameterDefinition[];
  documentationReference: string | null;
  manifestVersion: number;
  packageVersion: string;
  executionTarget: 'local-cpu' | 'local-gpu' | 'adapter';
  inspectorKind: 'none' | 'generic' | 'custom';
  customInspectorKey: string | null;
  capabilities?: string[];
}

export type DocumentationLanguage = 'en' | 'vi';

export interface AlgorithmDocumentation {
  algorithmId: string;
  language: DocumentationLanguage;
  content: string;
}

export interface WorkflowPoint {
  x: number;
  y: number;
}

export interface WorkflowPort {
  id: string;
  templateKey: string;
  direction: PortDirection;
  dataType: DataType;
  displayLabel: string;
  required: boolean;
  variadic: boolean;
  variadicInstanceIndex: number | null;
  channel: PortChannel;
  origin: PortOrigin;
  runtimeBinding: RuntimeBindingMode;
  runtimeKey: string | null;
  passthroughInputPortId: string | null;
}

export interface WorkflowNode {
  id: string;
  algorithmId: string;
  displayName: string;
  position: WorkflowPoint;
  parameters: Record<string, ParameterValue>;
  ports: WorkflowPort[];
}

export interface WorkflowConnection {
  id: string;
  sourceNodeId: string;
  sourcePortId: string;
  targetNodeId: string;
  targetPortId: string;
  kind?: 'data' | 'control';
  maxTraversals?: number | null;
  waypoints?: WorkflowPoint[];
}

export interface Workflow {
  recipeSlug: string;
  recipeName: string;
  version: number;
  revision: number;
  updatedAt: string;
  nodes: WorkflowNode[];
  connections: WorkflowConnection[];
  executionOrder: string[];
  migrationNotices: string[];
}

export type ValidationIssueCode =
  | 'unknown-algorithm'
  | 'unknown-node'
  | 'unknown-port'
  | 'duplicate-id'
  | 'duplicate-connection'
  | 'self-loop'
  | 'type-mismatch'
  | 'input-already-connected'
  | 'missing-required-input'
  | 'invalid-parameter'
  | 'generic-type-conflict'
  | 'unbounded-control-cycle'
  | 'cycle'
  | 'execution-order-mismatch'
  | 'dependency-order';

export interface ValidationIssue {
  code: ValidationIssueCode;
  message: string;
  nodeId?: string;
  portId?: string;
  connectionId?: string;
}

export interface ConnectionDraft {
  sourceNodeId: string;
  sourcePortId: string;
  targetNodeId: string;
  targetPortId: string;
  kind?: 'data' | 'control';
  maxTraversals?: number | null;
}