import type { WorkflowNode, WorkflowPort } from '../types/workflow';


export type CustomPortDraft = Pick<
  WorkflowPort,
  'templateKey' | 'displayLabel' | 'direction' | 'channel' | 'dataType'
  | 'runtimeBinding' | 'runtimeKey' | 'passthroughInputPortId'
>;

function assertEditable(port: WorkflowPort): void {
  if (port.origin === 'system') throw new Error('System port is locked and cannot be changed.');
}

function validatePort(node: WorkflowNode, port: WorkflowPort, ignoredPortId?: string): void {
  if (!port.templateKey.trim()) throw new Error('Port key is required.');
  if (node.ports.some((candidate) => candidate.id !== ignoredPortId && candidate.templateKey === port.templateKey)) {
    throw new Error('Port key must be unique within node.');
  }
  if (port.channel === 'control') {
    if (port.dataType !== 'generic' || port.runtimeBinding !== 'none') {
      throw new Error('Control ports require generic type and no runtime binding.');
    }
    return;
  }
  if (port.runtimeBinding === 'slot' && !port.runtimeKey?.trim()) {
    throw new Error('Slot-bound data ports require a runtime key.');
  }
  if (port.runtimeBinding === 'passthrough') {
    const source = node.ports.find((candidate) => candidate.id === port.passthroughInputPortId);
    if (port.direction !== 'output' || !source || source.direction !== 'input' || source.channel !== 'data') {
      throw new Error('Passthrough output requires an existing data input.');
    }
    if (source.dataType !== port.dataType) throw new Error('Passthrough input and output types must match.');
  }
}

export function addCustomPort(node: WorkflowNode, draft: CustomPortDraft): WorkflowNode {
  const port: WorkflowPort = {
    ...draft,
    id: crypto.randomUUID(),
    required: false,
    variadic: false,
    variadicInstanceIndex: null,
    origin: 'custom',
  };
  validatePort(node, port);
  return { ...node, ports: [...node.ports, port] };
}

export function updateCustomPort(
  node: WorkflowNode,
  portId: string,
  changes: Partial<CustomPortDraft>,
): WorkflowNode {
  const existing = node.ports.find((port) => port.id === portId);
  if (!existing) throw new Error('Port does not exist.');
  assertEditable(existing);
  const next = { ...existing, ...changes };
  if (next.channel === 'control') {
    next.dataType = 'generic';
    next.runtimeBinding = 'none';
    next.runtimeKey = null;
    next.passthroughInputPortId = null;
  }
  validatePort(node, next, portId);
  return { ...node, ports: node.ports.map((port) => port.id === portId ? next : port) };
}

export function removeCustomPort(node: WorkflowNode, portId: string): WorkflowNode {
  const existing = node.ports.find((port) => port.id === portId);
  if (!existing) throw new Error('Port does not exist.');
  assertEditable(existing);
  if (node.ports.some((port) => port.passthroughInputPortId === portId)) {
    throw new Error('Port is used by a passthrough output.');
  }
  return { ...node, ports: node.ports.filter((port) => port.id !== portId) };
}