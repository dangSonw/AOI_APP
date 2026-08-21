import { describe, expect, it } from 'vitest';
import type { AlgorithmDefinition, Workflow } from '../types/workflow';
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
});