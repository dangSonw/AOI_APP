import type { AlgorithmDefinition, Workflow } from '../types/workflow';
import { parseViewerDescriptor, type ViewerDescriptor } from '../types/visualization';

export interface WorkflowOutputViewer {
  key: string;
  nodeId: string;
  title: string;
  kind?: 'image' | 'plot-2d' | 'table' | 'heightmap';
  descriptor?: ViewerDescriptor;
}

export interface WorkflowOutputViewers {
  twoD: WorkflowOutputViewer[];
  threeD: WorkflowOutputViewer[];
  tables: WorkflowOutputViewer[];
}

interface ViewerNodeRun {
  nodeId: string;
  sequence: number;
  outputs: Record<string, unknown>;
}

function hasCapability(definition: AlgorithmDefinition | undefined, capability: string): boolean {
  return definition?.capabilities?.includes(capability) ?? false;
}

export function selectWorkflowOutputViewers(
  workflow: Workflow | null,
  definitions: AlgorithmDefinition[],
  nodeRuns: ViewerNodeRun[] = [],
): WorkflowOutputViewers {
  if (!workflow) return { twoD: [], threeD: [], tables: [] };
  const definitionsById = new Map(definitions.map((definition) => [definition.id, definition]));
  const twoD: WorkflowOutputViewer[] = [];
  const threeD: WorkflowOutputViewer[] = [];
  const tables: WorkflowOutputViewer[] = [];
  const latestRuns = new Map<string, ViewerNodeRun>();
  for (const run of nodeRuns) {
    const current = latestRuns.get(run.nodeId);
    if (!current || run.sequence > current.sequence) latestRuns.set(run.nodeId, run);
  }

  for (const node of workflow.nodes) {
    const definition = definitionsById.get(node.algorithmId);
    const title = node.displayName || definition?.name || node.algorithmId;
    let descriptor: ViewerDescriptor | undefined;
    const descriptorValue = latestRuns.get(node.id)?.outputs.viewerDescriptor
      ?? latestRuns.get(node.id)?.outputs['viewer-descriptor'];
    if (descriptorValue !== undefined) {
      try {
        const candidate = parseViewerDescriptor(descriptorValue);
        if (candidate.nodeInstanceId === node.id) descriptor = candidate;
      } catch {
        descriptor = undefined;
      }
    }
    const isLegacyImageOutput = definitions.length === 0 && node.algorithmId === 'image-output';
    if (hasCapability(definition, 'image-preview') || isLegacyImageOutput) {
      twoD.push({ key: node.id, nodeId: node.id, title });
    }
    if (hasCapability(definition, 'plot-2d-preview')) {
      twoD.push({ key: node.id, nodeId: node.id, title, kind: 'plot-2d', descriptor });
    }
    if (hasCapability(definition, 'table-preview')) {
      tables.push({ key: node.id, nodeId: node.id, title, kind: 'table', descriptor });
    }
    if (hasCapability(definition, '3d-preview')) {
      threeD.push({ key: node.id, nodeId: node.id, title, ...(descriptor?.kind === 'heightmap' ? { kind: 'heightmap' as const, descriptor } : {}) });
    }
  }

  return { twoD, threeD, tables };
}