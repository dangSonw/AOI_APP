import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { AlgorithmDefinition, WorkflowNode as WorkflowNodeValue } from '../../types/workflow';
import { WorkflowNode } from './WorkflowNode';

const value: WorkflowNodeValue = {
  id: 'node-1', algorithmId: 'logs', displayName: 'Logs', position: { x: 0, y: 0 },
  parameters: {}, ports: [],
};
const definition = {
  id: 'logs', name: 'Logs', description: '', category: 'Debugging', documentationGroup: 'Debugging',
  availability: 'configuration-only', use: 'debug', inputs: [], outputs: [], parameters: [],
  documentationReference: null, manifestVersion: 1, packageVersion: '1.0.0', executionTarget: 'local-cpu',
  inspectorKind: 'generic', customInspectorKey: null,
} satisfies AlgorithmDefinition;

describe('WorkflowNode editor presentation', () => {
  it('does not render runtime status or duration in the workflow editor', () => {
    const markup = renderToStaticMarkup(<WorkflowNode
      id="node-1"
      type="workflow"
      selected={false}
      dragging={false}
      draggable
      selectable
      deletable
      isConnectable
      zIndex={0}
      positionAbsoluteX={0}
      positionAbsoluteY={0}
      data={{
        value, definition, onRemove: vi.fn(),
      }}
    />);

    expect(markup).not.toContain('workflow-node--completed');
    expect(markup).not.toContain('Completed');
    expect(markup).not.toContain('17 ms');
  });
});