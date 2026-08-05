import { describe, expect, it, vi } from 'vitest';
import type { AlgorithmDefinition, Workflow, WorkflowConnection } from '../types/workflow';
import {
  createNodeFromDefinition,
  filterCatalog,
  isWorkflowDirty,
  moveExecutionNode,
  stableTopologicalOrder,
  validateConnection,
  validateDraft,
} from './workflow-graph';

const imageInput: AlgorithmDefinition = {
  id: 'image-input',
  name: 'Image input',
  description: 'Provides a recipe image.',
  category: 'Acquisition',
  documentationGroup: 'Acquisition and pipeline components',
  availability: 'configuration-only',
  inputs: [],
  outputs: [{ key: 'image', label: 'Image', direction: 'output', dataType: 'image', required: true, variadic: false }],
  parameters: [{ key: 'source', label: 'Source', kind: 'text', defaultValue: 'recipe-image', required: true, minimum: null, maximum: null, options: [], description: '' }],
  documentationReference: null,
};

const patchCore: AlgorithmDefinition = {
  id: 'patchcore',
  name: 'PatchCore',
  description: 'Representative feature memory bank.',
  category: 'Feature distribution',
  documentationGroup: 'Group B — Feature distribution',
  availability: 'configuration-only',
  inputs: [{ key: 'image', label: 'Image', direction: 'input', dataType: 'image', required: true, variadic: false }],
  outputs: [
    { key: 'anomaly-map', label: 'Anomaly map', direction: 'output', dataType: 'anomaly-map', required: true, variadic: false },
    { key: 'score', label: 'Score', direction: 'output', dataType: 'score', required: true, variadic: false },
  ],
  parameters: [{ key: 'memoryBankSize', label: 'Memory bank size', kind: 'integer', defaultValue: 10000, required: true, minimum: 1, maximum: 10000000, options: [], description: '' }],
  documentationReference: 'PatchCore',
};

const decisionFusion: AlgorithmDefinition = {
  id: 'decision-fusion',
  name: 'Decision fusion',
  description: 'Combines scores.',
  category: 'Decision',
  documentationGroup: 'Acquisition and pipeline components',
  availability: 'configuration-only',
  inputs: [{ key: 'scores', label: 'Scores', direction: 'input', dataType: 'score', required: true, variadic: true }],
  outputs: [{ key: 'decision', label: 'Decision', direction: 'output', dataType: 'decision', required: true, variadic: false }],
  parameters: [],
  documentationReference: null,
};

const catalog = [imageInput, patchCore, decisionFusion];

function makeWorkflow(): Workflow {
  const source = createNodeFromDefinition(imageInput, { x: 0, y: 0 });
  const detector = createNodeFromDefinition(patchCore, { x: 200, y: 0 });
  const fusion = createNodeFromDefinition(decisionFusion, { x: 400, y: 0 });
  const connections: WorkflowConnection[] = [
    {
      id: crypto.randomUUID(),
      sourceNodeId: source.id,
      sourcePortId: source.ports[0].id,
      targetNodeId: detector.id,
      targetPortId: detector.ports[0].id,
    },
    {
      id: crypto.randomUUID(),
      sourceNodeId: detector.id,
      sourcePortId: detector.ports[2].id,
      targetNodeId: fusion.id,
      targetPortId: fusion.ports[0].id,
    },
  ];
  return {
    recipeSlug: 'test-recipe',
    recipeName: 'Test recipe',
    version: 1,
    revision: 0,
    updatedAt: '2026-08-05T00:00:00Z',
    nodes: [source, detector, fusion],
    connections,
    executionOrder: [source.id, detector.id, fusion.id],
  };
}

describe('workflow graph helpers', () => {
  it('creates a node with catalog defaults and stable typed port instances', () => {
    vi.spyOn(crypto, 'randomUUID')
      .mockReturnValueOnce('00000000-0000-4000-8000-000000000001')
      .mockReturnValueOnce('00000000-0000-4000-8000-000000000002')
      .mockReturnValueOnce('00000000-0000-4000-8000-000000000003')
      .mockReturnValueOnce('00000000-0000-4000-8000-000000000004');

    const node = createNodeFromDefinition(patchCore, { x: 20, y: 40 });

    expect(node.id).toBe('00000000-0000-4000-8000-000000000001');
    expect(node.parameters.memoryBankSize).toBe(10000);
    expect(node.ports.map((port) => [port.templateKey, port.dataType])).toEqual([
      ['image', 'image'], ['anomaly-map', 'anomaly-map'], ['score', 'score'],
    ]);
  });

  it('rejects type mismatches, occupied inputs, and cycles', () => {
    const workflow = makeWorkflow();
    const [source, detector, fusion] = workflow.nodes;
    const alternateSource = createNodeFromDefinition(imageInput, { x: 0, y: 100 });

    expect(validateConnection(workflow, {
      sourceNodeId: source.id,
      sourcePortId: source.ports[0].id,
      targetNodeId: fusion.id,
      targetPortId: fusion.ports[0].id,
    })?.code).toBe('type-mismatch');
    expect(validateConnection({ ...workflow, nodes: [...workflow.nodes, alternateSource] }, {
      sourceNodeId: alternateSource.id,
      sourcePortId: alternateSource.ports[0].id,
      targetNodeId: detector.id,
      targetPortId: detector.ports[0].id,
    })?.code).toBe('input-already-connected');
    const cycleWorkflow: Workflow = {
      ...workflow,
      nodes: [source, detector, {
        ...fusion,
        ports: fusion.ports.map((port) => port.direction === 'output' ? { ...port, dataType: 'image' } : port),
      }],
      connections: workflow.connections.slice(1),
    };
    expect(validateConnection(cycleWorkflow, {
      sourceNodeId: fusion.id,
      sourcePortId: fusion.ports[1]?.id ?? fusion.ports[0].id,
      targetNodeId: detector.id,
      targetPortId: detector.ports[0].id,
    })?.code).toBe('cycle');
  });

  it('orders deterministically, validates dependencies, and moves one execution item', () => {
    const workflow = makeWorkflow();
    const reversed = [workflow.nodes[2].id, workflow.nodes[1].id, workflow.nodes[0].id];

    expect(stableTopologicalOrder(workflow, reversed)).toEqual(workflow.executionOrder);
    expect(validateDraft({ ...workflow, executionOrder: reversed }, catalog).map((issue) => issue.code)).toContain('dependency-order');
    expect(moveExecutionNode(workflow.executionOrder, workflow.nodes[1].id, -1)).toEqual([
      workflow.nodes[1].id, workflow.nodes[0].id, workflow.nodes[2].id,
    ]);
  });

  it('filters every operator-facing catalog field without case sensitivity', () => {
    expect(filterCatalog(catalog, 'PATCHCORE')).toEqual([patchCore]);
    expect(filterCatalog(catalog, 'representative')).toEqual([patchCore]);
    expect(filterCatalog(catalog, 'feature distribution')).toEqual([patchCore]);
    expect(filterCatalog(catalog, '')).toEqual(catalog);
  });

  it('derives dirty state from persisted AOI values', () => {
    const saved = makeWorkflow();
    expect(isWorkflowDirty(saved, structuredClone(saved))).toBe(false);
    expect(isWorkflowDirty(saved, { ...saved, recipeName: 'Changed' })).toBe(true);
  });
});