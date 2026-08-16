import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { AlgorithmDefinition } from '../../types/workflow';
import { NodeDocumentationDialog } from './NodeDocumentationDialog';


const definition: AlgorithmDefinition = {
  id: 'camera-capture', name: 'Camera capture', description: 'Capture image', category: 'Acquisition',
  documentationGroup: 'Acquisition', availability: 'configuration-only', use: 'debug', inputs: [], outputs: [], parameters: [],
  documentationReference: null, manifestVersion: 1, packageVersion: '1.0.0', executionTarget: 'adapter',
  inspectorKind: 'custom', customInspectorKey: 'camera-acquisition',
};

describe('NodeDocumentationDialog', () => {
  it('renders a bilingual node-specific README dialog shell', () => {
    const markup = renderToStaticMarkup(
      <NodeDocumentationDialog accessToken="token" definition={definition} onClose={vi.fn()} />,
    );

    expect(markup).toContain('role="dialog"');
    expect(markup).toContain('Node README');
    expect(markup).toContain('Camera capture');
    expect(markup).toContain('camera-capture');
    expect(markup).toContain('Tiếng Việt');
    expect(markup).toContain('English');
  });

  it('renders nothing without a selected tool', () => {
    expect(renderToStaticMarkup(<NodeDocumentationDialog accessToken="token" definition={null} onClose={vi.fn()} />)).toBe('');
  });
});