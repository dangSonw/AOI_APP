import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { ReactFlowProvider } from '@xyflow/react';
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

  it('renders the inferred virtual pin data type', () => {
    const pinDefinition = {
      ...definition,
      id: 'output-pin',
      name: 'Output Pin',
      category: 'Workflow routing',
      outputs: [{ key: 'value', label: 'Value', direction: 'output', dataType: 'generic', required: true, variadic: false }],
    } satisfies AlgorithmDefinition;
    const pinValue = {
      ...value,
      algorithmId: 'output-pin',
      displayName: 'Camera',
       ports: [
         {
           id: 'value', templateKey: 'value', direction: 'output', dataType: 'generic', displayLabel: 'Value',
           required: true, variadic: false, variadicInstanceIndex: null, channel: 'data', origin: 'default',
           runtimeBinding: 'slot', runtimeKey: 'value', passthroughInputPortId: null,
         },
         {
           id: 'success', templateKey: 'success', direction: 'output', dataType: 'generic', displayLabel: 'Success',
           required: false, variadic: false, variadicInstanceIndex: null, channel: 'control', origin: 'system',
           runtimeBinding: 'none', runtimeKey: null, passthroughInputPortId: null,
         },
       ],
    } satisfies WorkflowNodeValue;
    const markup = renderToStaticMarkup(
      <ReactFlowProvider>
        <WorkflowNode
          id="node-1" type="workflow" selected={false} dragging={false} draggable selectable deletable isConnectable
          zIndex={0} positionAbsoluteX={0} positionAbsoluteY={0}
          data={{ value: pinValue, definition: pinDefinition, onRemove: vi.fn(), inferredDataType: 'image' }}
        />
      </ReactFlowProvider>,
    );

    expect(markup).toContain('image · inferred');
    expect(markup).toContain('<strong>Success</strong><small>generic');
    expect(markup).not.toContain('<strong>Success</strong><small>image · inferred');
  });
});