import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { AlgorithmDefinition, WorkflowNode } from '../../types/workflow';
import { knnImageSegmentationPlugin } from './index';

const node: WorkflowNode = {
  id: 'knn-node', algorithmId: 'knn-image-segmentation', displayName: 'Segment', position: { x: 0, y: 0 },
  parameters: {
    foregroundLabels: ['object'],
    trainingSamples: [{ label: 'background', color: [0, 0, 0] }, { label: 'object', color: [255, 255, 255] }],
  },
  ports: [],
};

const definition = {
  id: 'knn-image-segmentation', name: 'KNN image segmentation', description: 'Segment', category: 'Segmentation',
  documentationGroup: 'Segmentation', availability: 'configuration-only', use: 'debug', inputs: [], outputs: [], parameters: [],
  documentationReference: null, manifestVersion: 1, packageVersion: '1.0.0', executionTarget: 'local-cpu',
  inspectorKind: 'custom', customInspectorKey: 'knn-image-segmentation',
} satisfies AlgorithmDefinition;

describe('KNN image segmentation plugin', () => {
  it('exports the stable node ID and existing feature UI', () => {
    const Inspector = knnImageSegmentationPlugin.Inspector;
    expect(Inspector).toBeDefined();
    if (!Inspector) throw new Error('KNN image segmentation inspector is not registered.');
    const markup = renderToStaticMarkup(<Inspector node={node} definition={definition} updateParameter={vi.fn()} />);
    expect(knnImageSegmentationPlugin.nodeId).toBe('knn-image-segmentation');
    expect(markup).toContain('KNN color features');
    expect(markup).toContain('Foreground features');
  });
});