import { describe, expect, it, vi } from 'vitest';
import type { AlgorithmDefinition, Workflow, WorkflowConnection } from '../types/workflow';
import {
  addConnection,
  createNodeFromDefinition,
  filterCatalog,
  isWorkflowDirty,
  moveExecutionNode,
  resolveVirtualPinTypes,
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
  use: 'test',
  inputs: [],
  outputs: [{ key: 'image', label: 'Image', direction: 'output', dataType: 'image', required: true, variadic: false }],
  parameters: [{ key: 'source', label: 'Source', kind: 'text', defaultValue: 'recipe-image', required: true, minimum: null, maximum: null, options: [], description: '' }],
  manifestVersion: 1, packageVersion: '1.0.0', executionTarget: 'local-cpu', inspectorKind: 'generic', customInspectorKey: null,
  documentationReference: null,
};

const patchCore: AlgorithmDefinition = {
  id: 'patchcore',
  name: 'PatchCore',
  description: 'Representative feature memory bank.',
  category: 'Feature distribution',
  documentationGroup: 'Group B — Feature distribution',
  availability: 'configuration-only',
  use: 'test',
  inputs: [{ key: 'image', label: 'Image', direction: 'input', dataType: 'image', required: true, variadic: false }],
  outputs: [
    { key: 'anomaly-map', label: 'Anomaly map', direction: 'output', dataType: 'anomaly-map', required: true, variadic: false },
    { key: 'score', label: 'Score', direction: 'output', dataType: 'score', required: true, variadic: false },
  ],
  parameters: [{ key: 'memoryBankSize', label: 'Memory bank size', kind: 'integer', defaultValue: 10000, required: true, minimum: 1, maximum: 10000000, options: [], description: '' }],
  manifestVersion: 1, packageVersion: '1.0.0', executionTarget: 'local-cpu', inspectorKind: 'generic', customInspectorKey: null,
  documentationReference: 'PatchCore',
};

const decisionFusion: AlgorithmDefinition = {
  id: 'decision-fusion',
  name: 'Decision fusion',
  description: 'Combines scores.',
  category: 'Decision',
  documentationGroup: 'Acquisition and pipeline components',
  availability: 'configuration-only',
  use: 'test',
  inputs: [{ key: 'scores', label: 'Scores', direction: 'input', dataType: 'score', required: true, variadic: true }],
  outputs: [{ key: 'decision', label: 'Decision', direction: 'output', dataType: 'decision', required: true, variadic: false }],
  parameters: [],
  manifestVersion: 1, packageVersion: '1.0.0', executionTarget: 'local-cpu', inspectorKind: 'generic', customInspectorKey: null,
  documentationReference: null,
};

const inputPin: AlgorithmDefinition = {
  id: 'input-pin', name: 'Input Pin', description: 'Starts a named virtual data channel.',
  category: 'Workflow routing', documentationGroup: 'Workflow routing', availability: 'configuration-only', use: 'debug',
  inputs: [{ key: 'value', label: 'Value', direction: 'input', dataType: 'generic', required: true, variadic: false }],
  outputs: [], parameters: [], documentationReference: null,
  manifestVersion: 1, packageVersion: '1.0.0', executionTarget: 'local-cpu', inspectorKind: 'generic', customInspectorKey: null,
};

const outputPin: AlgorithmDefinition = {
  id: 'output-pin', name: 'Output Pin', description: 'Continues a named virtual data channel.',
  category: 'Workflow routing', documentationGroup: 'Workflow routing', availability: 'configuration-only', use: 'debug',
  inputs: [],
  outputs: [{ key: 'value', label: 'Value', direction: 'output', dataType: 'generic', required: true, variadic: false }],
  parameters: [], documentationReference: null,
  manifestVersion: 1, packageVersion: '1.0.0', executionTarget: 'local-cpu', inspectorKind: 'generic', customInspectorKey: null,
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
    migrationNotices: [],
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
    expect(node.ports.filter((port) => port.channel === 'data').map((port) => [port.templateKey, port.dataType])).toEqual([
      ['image', 'image'], ['anomaly-map', 'anomaly-map'], ['score', 'score'],
    ]);
    expect(node.ports.filter((port) => port.channel === 'control').map((port) => port.templateKey)).toEqual([
      'trigger', 'success', 'failure',
    ]);
  });

  it('creates virtual pin instances with the shared default channel name', () => {
    const input = createNodeFromDefinition(inputPin, { x: 0, y: 0 });
    const output = createNodeFromDefinition(outputPin, { x: 200, y: 0 });

    expect(input.displayName).toBe('Pin');
    expect(output.displayName).toBe('Pin');
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

  it('accepts success control output connected to a Logs trigger without dependency-order errors', () => {
    const logs: AlgorithmDefinition = {
      id: 'logs', name: 'Logs', description: 'Writes a message.', category: 'Debugging',
      documentationGroup: 'Debugging and observability', availability: 'configuration-only', use: 'debug',
      inputs: [], outputs: [], parameters: [], documentationReference: null,
      manifestVersion: 1, packageVersion: '1.0.0', executionTarget: 'local-cpu',
      inspectorKind: 'generic', customInspectorKey: null,
    };
    const source = createNodeFromDefinition(imageInput, { x: 0, y: 0 });
    const logNode = createNodeFromDefinition(logs, { x: 200, y: 0 });
    const success = source.ports.find((port) => port.templateKey === 'success')!;
    const trigger = logNode.ports.find((port) => port.templateKey === 'trigger')!;
    const workflow: Workflow = {
      recipeSlug: 'logs-control', recipeName: 'Logs control', version: 2, revision: 0,
      updatedAt: new Date(0).toISOString(), nodes: [source, logNode],
      connections: [{
        id: crypto.randomUUID(), sourceNodeId: source.id, sourcePortId: success.id,
        targetNodeId: logNode.id, targetPortId: trigger.id, kind: 'control',
      }],
      executionOrder: [logNode.id, source.id], migrationNotices: [],
    };

    expect(validateConnection({ ...workflow, connections: [] }, workflow.connections[0])).toBeNull();
    expect(validateDraft(workflow, [imageInput, logs]).map((item) => item.code)).not.toContain('dependency-order');

    const persisted = addConnection({ ...workflow, connections: [] }, {
      sourceNodeId: source.id, sourcePortId: success.id,
      targetNodeId: logNode.id, targetPortId: trigger.id,
    });
    expect(persisted.connections[0].kind).toBe('control');
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

  it('infers named virtual pin types and includes the virtual dependency in auto order', () => {
    const source = createNodeFromDefinition(imageInput, { x: 0, y: 0 });
    const input = { ...createNodeFromDefinition(inputPin, { x: 200, y: 0 }), displayName: ' Camera ' };
    const output = { ...createNodeFromDefinition(outputPin, { x: 400, y: 0 }), displayName: 'Camera' };
    const detector = createNodeFromDefinition(patchCore, { x: 600, y: 0 });
    const workflow: Workflow = {
      recipeSlug: 'virtual-pins', recipeName: 'Virtual pins', version: 2, revision: 0,
      updatedAt: new Date(0).toISOString(), nodes: [source, input, output, detector],
      connections: [
        {
          id: crypto.randomUUID(), sourceNodeId: source.id, sourcePortId: source.ports[0].id,
          targetNodeId: input.id, targetPortId: input.ports[0].id, kind: 'data',
        },
        {
          id: crypto.randomUUID(), sourceNodeId: output.id, sourcePortId: output.ports[0].id,
          targetNodeId: detector.id, targetPortId: detector.ports[0].id, kind: 'data',
        },
      ],
      executionOrder: [source.id, input.id, output.id, detector.id], migrationNotices: [],
    };

    expect(validateDraft(workflow, [imageInput, inputPin, outputPin, patchCore])).toEqual([]);
    expect(stableTopologicalOrder(workflow, [detector.id, output.id, input.id, source.id])).toEqual([
      source.id, input.id, output.id, detector.id,
    ]);
    expect(resolveVirtualPinTypes(workflow)).toEqual(new Map([
      [input.id, 'image'],
      [output.id, 'image'],
    ]));
  });

  it('rejects unmatched, duplicate, case-mismatched, and conflicting virtual pins', () => {
    const source = createNodeFromDefinition(imageInput, { x: 0, y: 0 });
    const input = { ...createNodeFromDefinition(inputPin, { x: 200, y: 0 }), displayName: 'Frame' };
    const duplicateInput = { ...createNodeFromDefinition(inputPin, { x: 200, y: 100 }), displayName: ' Frame ' };
    const output = { ...createNodeFromDefinition(outputPin, { x: 400, y: 0 }), displayName: 'frame' };
    const fusion = createNodeFromDefinition(decisionFusion, { x: 600, y: 0 });
    const workflow: Workflow = {
      recipeSlug: 'invalid-pins', recipeName: 'Invalid pins', version: 2, revision: 0,
      updatedAt: new Date(0).toISOString(), nodes: [source, input, duplicateInput, output, fusion],
      connections: [
        {
          id: crypto.randomUUID(), sourceNodeId: source.id, sourcePortId: source.ports[0].id,
          targetNodeId: input.id, targetPortId: input.ports[0].id, kind: 'data',
        },
        {
          id: crypto.randomUUID(), sourceNodeId: source.id, sourcePortId: source.ports[0].id,
          targetNodeId: duplicateInput.id, targetPortId: duplicateInput.ports[0].id, kind: 'data',
        },
        {
          id: crypto.randomUUID(), sourceNodeId: output.id, sourcePortId: output.ports[0].id,
          targetNodeId: fusion.id, targetPortId: fusion.ports[0].id, kind: 'data',
        },
      ],
      executionOrder: [source.id, input.id, duplicateInput.id, output.id, fusion.id], migrationNotices: [],
    };

    const issues = validateDraft(workflow, [imageInput, inputPin, outputPin, decisionFusion]);
    expect(issues.filter((item) => item.code === 'invalid-parameter').map((item) => item.message)).toEqual(expect.arrayContaining([
      expect.stringContaining('exactly one Input Pin'),
      expect.stringContaining('matching Input Pin'),
    ]));
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