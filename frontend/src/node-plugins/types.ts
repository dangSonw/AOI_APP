import type { AlgorithmDefinition, ParameterValue, WorkflowNode } from '../types/workflow';

export interface NodeInspectorPluginProps {
  node: WorkflowNode;
  definition: AlgorithmDefinition;
  updateParameter: (key: string, value: ParameterValue) => void;
}

export type NodeInspectorPlugin = (props: NodeInspectorPluginProps) => JSX.Element;
