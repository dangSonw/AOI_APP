import { describe, expect, it } from 'vitest';
import type { AlgorithmDefinition, Workflow } from '../types/workflow';
import type { ViewerDescriptor } from '../types/visualization';
import { selectWorkflowOutputViewers } from './workflow-output-viewers';

const baseDefinition: AlgorithmDefinition = {
  id: 'image-output',
  name: 'Image output',
  description: 'Preview output',
  category: 'Visualization',
  documentationGroup: 'Visualization',
  availability: 'configuration-only',
  use: 'debug',
  inputs: [],
  outputs: [],
  parameters: [],
  documentationReference: null,
  manifestVersion: 1,
  packageVersion: '1.0.0',
  executionTarget: 'local-cpu',
  inspectorKind: 'none',
  customInspectorKey: null,
  capabilities: ['image-preview'],
  actions: {},
  artifactContracts: {},
};

const workflow: Workflow = {
  recipeSlug: 'recipe',
  recipeName: 'Recipe',
  version: 1,
  revision: 1,
  updatedAt: new Date(0).toISOString(),
  nodes: [
    { id: 'image-1', algorithmId: 'image-output', displayName: 'Board image', position: { x: 0, y: 0 }, parameters: {}, ports: [] },
    { id: 'image-2', algorithmId: 'image-output', displayName: 'Anomaly image', position: { x: 0, y: 0 }, parameters: {}, ports: [] },
    { id: 'logs', algorithmId: 'logs', displayName: 'Logs', position: { x: 0, y: 0 }, parameters: {}, ports: [] },
  ],
  connections: [],
  executionOrder: ['image-1', 'image-2', 'logs'],
  migrationNotices: [],
};

describe('workflow output viewers', () => {
  it('creates one 2D viewer for every image preview node', () => {
    const result = selectWorkflowOutputViewers(workflow, [baseDefinition]);

    expect(result.twoD).toHaveLength(2);
    expect(result.twoD.map((viewer) => viewer.key)).toEqual(['image-1', 'image-2']);
    expect(result.threeD).toHaveLength(0);
  });

  it('does not render a viewer when the image output node is absent', () => {
    const result = selectWorkflowOutputViewers(
      { ...workflow, nodes: workflow.nodes.filter((node) => node.algorithmId !== 'image-output') },
      [baseDefinition],
    );

    expect(result.twoD).toEqual([]);
    expect(result.threeD).toEqual([]);
  });

  it('does not treat a generic output pin as a 2D viewer', () => {
    const outputPin = {
      ...workflow.nodes[2],
      id: 'output-pin-1',
      algorithmId: 'output-pin',
      displayName: 'Camera',
    };
    const result = selectWorkflowOutputViewers(
      { ...workflow, nodes: [outputPin] },
      [baseDefinition],
    );

    expect(result.twoD).toEqual([]);
    expect(result.threeD).toEqual([]);
  });

  it('only creates a 3D viewer for an explicit 3D preview capability', () => {
    const threeDDefinition: AlgorithmDefinition = {
      ...baseDefinition,
      id: 'heightmap-output',
      name: '3D output',
      capabilities: ['3d-preview'],
    };
    const threeDNode = { ...workflow.nodes[0], id: 'heightmap-1', algorithmId: 'heightmap-output', displayName: 'Heightmap' };

    const result = selectWorkflowOutputViewers(
      { ...workflow, nodes: [...workflow.nodes, threeDNode] },
      [baseDefinition, threeDDefinition],
    );

    expect(result.threeD).toEqual([{ key: 'heightmap-1', nodeId: 'heightmap-1', title: 'Heightmap' }]);
  });

  it('attaches a matching typed heightmap descriptor to an explicit 3D viewer', () => {
    const definition = { ...baseDefinition, id: 'heightmap-output', capabilities: ['3d-preview'] };
    const node = { ...workflow.nodes[0], id: 'heightmap-1', algorithmId: 'heightmap-output', displayName: 'Heightmap' };
    const descriptor: ViewerDescriptor = {
      nodeInstanceId: node.id, title: 'Surface', kind: 'heightmap', schema: 'aoi.heightmap.v1',
      artifactEndpoint: '/api/v1/research/artifacts/9', width: 640, height: 360,
      xLabel: 'X', yLabel: 'Y', xUnit: 'mm', yUnit: 'mm', interactions: ['focus', 'pan', 'zoom'], fallbackMediaType: 'image/png',
    };

    const result = selectWorkflowOutputViewers(
      { ...workflow, nodes: [node] }, [definition],
      [{ nodeId: node.id, sequence: 1, outputs: { viewerDescriptor: descriptor } }],
    );

    expect(result.threeD).toEqual([{ key: node.id, nodeId: node.id, title: 'Heightmap', kind: 'heightmap', descriptor }]);
  });

  it('creates capability-driven plot and table viewers with descriptors from the matching node run', () => {
    const plotDefinition: AlgorithmDefinition = {
      ...baseDefinition, id: 'plot-2d-output', name: 'Plot output', capabilities: ['plot-2d-preview'],
    };
    const tableDefinition: AlgorithmDefinition = {
      ...baseDefinition, id: 'table-output', name: 'Table output', capabilities: ['table-preview'],
    };
    const plotDescriptor: ViewerDescriptor = {
      nodeInstanceId: 'plot-1', title: 'Confusion matrix', kind: 'plot-2d', schema: 'aoi.confusion-matrix.v1',
      artifactEndpoint: '/api/v1/research/artifacts/7', width: 640, height: 360,
      xLabel: 'Predicted', yLabel: 'Actual', xUnit: '', yUnit: '', interactions: ['focus'], fallbackMediaType: 'image/png',
    };
    const tableDescriptor: ViewerDescriptor = {
      nodeInstanceId: 'table-1', title: 'Classification report', kind: 'table', schema: 'aoi.table.v1',
      artifactEndpoint: '/api/v1/research/artifacts/8', width: null, height: null,
      xLabel: '', yLabel: '', xUnit: '', yUnit: '', interactions: [], fallbackMediaType: null,
    };
    const nodes = [
      ...workflow.nodes,
      { ...workflow.nodes[0], id: 'plot-1', algorithmId: 'plot-2d-output', displayName: 'Plot' },
      { ...workflow.nodes[0], id: 'table-1', algorithmId: 'table-output', displayName: 'Report' },
    ];

    const result = selectWorkflowOutputViewers(
      { ...workflow, nodes },
      [baseDefinition, plotDefinition, tableDefinition],
      [
        { nodeId: 'plot-1', sequence: 4, outputs: { viewerDescriptor: plotDescriptor } },
        { nodeId: 'table-1', sequence: 5, outputs: { viewerDescriptor: tableDescriptor } },
      ],
    );

    expect(result.twoD.find((viewer) => viewer.key === 'plot-1')).toMatchObject({ kind: 'plot-2d', descriptor: plotDescriptor });
    expect(result.tables).toEqual([{ key: 'table-1', nodeId: 'table-1', title: 'Report', kind: 'table', descriptor: tableDescriptor }]);
  });

  it('creates multiple explicit structured viewers but never creates one from a generic output pin', () => {
    const plotDefinition = { ...baseDefinition, id: 'plot-2d-output', capabilities: ['plot-2d-preview'] };
    const genericDefinition = { ...baseDefinition, id: 'output-pin', capabilities: [] };
    const plotNodes = ['plot-1', 'plot-2'].map((id) => ({
      ...workflow.nodes[0], id, algorithmId: 'plot-2d-output', displayName: id,
    }));
    const genericNode = { ...workflow.nodes[0], id: 'generic-1', algorithmId: 'output-pin' };

    const result = selectWorkflowOutputViewers(
      { ...workflow, nodes: [...plotNodes, genericNode] },
      [plotDefinition, genericDefinition],
      [{ nodeId: 'generic-1', sequence: 1, outputs: { viewerDescriptor: { kind: 'plot-2d' } } }],
    );

    expect(result.twoD.map((viewer) => viewer.key)).toEqual(['plot-1', 'plot-2']);
    expect(result.tables).toEqual([]);
  });
});