import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { AlgorithmDefinition, WorkflowNode } from '../../types/workflow';
import { NodeInspector } from './NodeInspector';

const node: WorkflowNode = {
  id: 'node-1', algorithmId: 'camera-capture', displayName: 'Capture', position: { x: 0, y: 0 },
  parameters: { cameraId: 'top-camera' }, ports: [],
};
const baseDefinition: AlgorithmDefinition = {
  id: 'camera-capture', name: 'Camera capture', description: 'Capture image', category: 'Acquisition',
  documentationGroup: 'Acquisition', availability: 'configuration-only', use: 'test', inputs: [], outputs: [],
  parameters: [{ key: 'cameraId', label: 'Camera ID', kind: 'text', defaultValue: 'top-camera', required: true, minimum: null, maximum: null, options: [], description: '' }],
  documentationReference: null, manifestVersion: 1, packageVersion: '1.0.0', executionTarget: 'adapter',
  inspectorKind: 'generic', customInspectorKey: null,
  controlPorts: [],
};

describe('NodeInspector plugin contract', () => {
  it('renders generic controls from the manifest schema', () => {
    const markup = renderToStaticMarkup(<NodeInspector node={node} definition={baseDefinition} onChange={vi.fn()} />);
    expect(markup).toContain('Camera ID');
  });

  it('renders registered custom inspectors through safe typed props', () => {
    const definition = { ...baseDefinition, inspectorKind: 'custom' as const, customInspectorKey: 'camera-acquisition' };
    const markup = renderToStaticMarkup(<NodeInspector node={node} definition={definition} onChange={vi.fn()} />);
    expect(markup).toContain('Camera acquisition profile');
    expect(markup).not.toContain('filesystem');
    expect(markup).not.toContain('shell');
  });

  it('keeps shared identity and ports while leaving plugin content empty for none', () => {
    const definition = { ...baseDefinition, parameters: [], inspectorKind: 'none' as const, customInspectorKey: null };
    const markup = renderToStaticMarkup(<NodeInspector node={node} definition={definition} onChange={vi.fn()} />);
    expect(markup).toContain('Display name');
    expect(markup).toContain('Port labels');
    expect(markup).toContain('data-inspector-content="empty"');
    expect(markup).not.toContain('This method has no configurable parameters.');
  });

  it('renders custom port editor and marks system ports as locked', () => {
    const withPorts: WorkflowNode = {
      ...node,
      ports: [{
        id: 'trigger', templateKey: 'trigger', direction: 'input', dataType: 'generic',
        displayLabel: 'Trigger', required: false, variadic: false, variadicInstanceIndex: null,
        channel: 'control', origin: 'system', runtimeBinding: 'none', runtimeKey: null,
        passthroughInputPortId: null,
      }],
    };
    const markup = renderToStaticMarkup(<NodeInspector node={withPorts} definition={baseDefinition} onChange={vi.fn()} />);

    expect(markup).toContain('Add custom port');
    expect(markup).toContain('System port · locked');
    expect(markup).not.toContain('Remove custom port');
  });
});
