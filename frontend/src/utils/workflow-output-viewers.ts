import type { AlgorithmDefinition, Workflow } from '../types/workflow';

export interface WorkflowOutputViewer {
  key: string;
  nodeId: string;
  title: string;
}

export interface WorkflowOutputViewers {
  twoD: WorkflowOutputViewer[];
  threeD: WorkflowOutputViewer[];
}

function hasCapability(definition: AlgorithmDefinition | undefined, capability: string): boolean {
  return definition?.capabilities?.includes(capability) ?? false;
}

export function selectWorkflowOutputViewers(
  workflow: Workflow | null,
  definitions: AlgorithmDefinition[],
): WorkflowOutputViewers {
  if (!workflow) return { twoD: [], threeD: [] };
  const definitionsById = new Map(definitions.map((definition) => [definition.id, definition]));
  const twoD: WorkflowOutputViewer[] = [];
  const threeD: WorkflowOutputViewer[] = [];

  for (const node of workflow.nodes) {
    const definition = definitionsById.get(node.algorithmId);
    const isLegacyImageOutput = definitions.length === 0 && node.algorithmId === 'image-output';
    if (hasCapability(definition, 'image-preview') || isLegacyImageOutput) {
      twoD.push({ key: node.id, nodeId: node.id, title: node.displayName || definition?.name || node.algorithmId });
    }
    if (hasCapability(definition, '3d-preview')) {
      threeD.push({ key: node.id, nodeId: node.id, title: node.displayName || definition?.name || node.algorithmId });
    }
  }

  return { twoD, threeD };
}