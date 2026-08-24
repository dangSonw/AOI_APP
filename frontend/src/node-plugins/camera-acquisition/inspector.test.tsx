import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { AlgorithmDefinition, WorkflowNode } from '../../types/workflow';
import { cameraAcquisitionPlugin } from './index';

const node: WorkflowNode = {
  id: 'camera-node', algorithmId: 'camera-capture', displayName: 'Capture', position: { x: 0, y: 0 },
  parameters: { cameraId: 'top-camera' }, ports: [],
};

const definition = {
  id: 'camera-capture', name: 'Camera capture', description: 'Capture', category: 'Acquisition',
  documentationGroup: 'Acquisition', availability: 'configuration-only', use: 'test', inputs: [], outputs: [], parameters: [],
  documentationReference: null, manifestVersion: 1, packageVersion: '1.0.0', executionTarget: 'adapter',
  inspectorKind: 'custom', customInspectorKey: 'camera-acquisition',
} satisfies AlgorithmDefinition;

describe('camera acquisition plugin', () => {
  it('exports the stable node ID and existing inspector UI', () => {
    const Inspector = cameraAcquisitionPlugin.Inspector;
    expect(Inspector).toBeDefined();
    if (!Inspector) throw new Error('Camera acquisition inspector is not registered.');
    const markup = renderToStaticMarkup(<Inspector node={node} definition={definition} updateParameter={vi.fn()} />);
    expect(cameraAcquisitionPlugin.nodeId).toBe('camera-acquisition');
    expect(markup).toContain('Camera acquisition profile');
    expect(markup).toContain('top-camera');
  });
});