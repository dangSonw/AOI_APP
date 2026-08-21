import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import type { AlgorithmDefinition, DataType, WorkflowNode as WorkflowNodeValue } from '../../types/workflow';
import { RuntimeUseBadge } from '../RuntimeUseBadge';


export interface WorkflowNodeData extends Record<string, unknown> {
  value: WorkflowNodeValue;
  definition: AlgorithmDefinition;
  onRemove: (nodeId: string) => void;
  inferredDataType?: DataType;
}

export type WorkflowFlowNode = Node<WorkflowNodeData, 'workflow'>;

export function WorkflowNode({ id, data, selected }: NodeProps<WorkflowFlowNode>) {
  const inputs = data.value.ports.filter((port) => port.direction === 'input');
  const outputs = data.value.ports.filter((port) => port.direction === 'output');
  const typeLabel = (dataType: DataType, channel: 'data' | 'control') => channel === 'data'
    && data.inferredDataType && data.inferredDataType !== 'generic'
    ? `${data.inferredDataType} · inferred`
    : dataType;
  return (
    <article className={`workflow-node ${selected ? 'workflow-node--selected' : ''}`} aria-label={`${data.value.displayName} workflow node`}>
      <header>
        <div><span>{data.value.algorithmId}</span><strong>{data.value.displayName}</strong></div>
        <button className="nodrag workflow-node__remove" type="button" onClick={() => data.onRemove(id)} aria-label={`Remove ${data.value.displayName}`}>×</button>
      </header>
      <div className="workflow-node__availability"><RuntimeUseBadge use={data.definition.use} /></div>
      <div className="workflow-node__ports">
        <div>
          {inputs.map((port) => (
            <div className="workflow-port workflow-port--input" key={port.id}>
              <Handle id={port.id} type="target" position={Position.Left} title={`${port.displayLabel}: ${typeLabel(port.dataType, port.channel)}`} />
              <span><strong>{port.displayLabel}</strong><small>{typeLabel(port.dataType, port.channel)}{port.required ? ' · required' : ''}</small></span>
            </div>
          ))}
        </div>
        <div>
          {outputs.map((port) => (
            <div className="workflow-port workflow-port--output" key={port.id}>
              <span><strong>{port.displayLabel}</strong><small>{typeLabel(port.dataType, port.channel)}</small></span>
              <Handle id={port.id} type="source" position={Position.Right} title={`${port.displayLabel}: ${typeLabel(port.dataType, port.channel)}`} />
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}