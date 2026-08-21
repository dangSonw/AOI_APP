import type { DataType, Workflow, WorkflowNode } from '../types/workflow';


export const INPUT_PIN_ID = 'input-pin';
export const OUTPUT_PIN_ID = 'output-pin';

export interface VirtualPinGroup {
  name: string;
  inputNodes: WorkflowNode[];
  outputNodes: WorkflowNode[];
  concreteTypes: Set<DataType>;
  inferredType: DataType;
}

export function normalizeVirtualPinName(node: WorkflowNode): string {
  return node.displayName.trim();
}

export function resolveVirtualPinGroups(workflow: Workflow): VirtualPinGroup[] {
  const grouped = new Map<string, { inputNodes: WorkflowNode[]; outputNodes: WorkflowNode[] }>();
  for (const node of workflow.nodes) {
    if (node.algorithmId !== INPUT_PIN_ID && node.algorithmId !== OUTPUT_PIN_ID) continue;
    const name = normalizeVirtualPinName(node);
    const group = grouped.get(name) ?? { inputNodes: [], outputNodes: [] };
    (node.algorithmId === INPUT_PIN_ID ? group.inputNodes : group.outputNodes).push(node);
    grouped.set(name, group);
  }

  const nodes = new Map(workflow.nodes.map((node) => [node.id, node]));
  const ports = new Map(workflow.nodes.flatMap((node) => node.ports.map((port) => [`${node.id}:${port.id}`, port] as const)));
  return [...grouped.entries()].map(([name, members]) => {
    const concreteTypes = new Set<DataType>();
    for (const node of [...members.inputNodes, ...members.outputNodes]) {
      for (const port of node.ports) {
        if (port.channel === 'data' && port.dataType !== 'generic') concreteTypes.add(port.dataType);
      }
    }
    for (const connection of workflow.connections) {
      if ((connection.kind ?? 'data') !== 'data') continue;
      const sourceNode = nodes.get(connection.sourceNodeId);
      const targetNode = nodes.get(connection.targetNodeId);
      const sourcePort = ports.get(`${connection.sourceNodeId}:${connection.sourcePortId}`);
      const targetPort = ports.get(`${connection.targetNodeId}:${connection.targetPortId}`);
      if (!sourceNode || !targetNode || !sourcePort || !targetPort) continue;
      if (targetNode.algorithmId === INPUT_PIN_ID && normalizeVirtualPinName(targetNode) === name && sourcePort.dataType !== 'generic') {
        concreteTypes.add(sourcePort.dataType);
      }
      if (sourceNode.algorithmId === OUTPUT_PIN_ID && normalizeVirtualPinName(sourceNode) === name && targetPort.dataType !== 'generic') {
        concreteTypes.add(targetPort.dataType);
      }
    }
    return {
      name,
      ...members,
      concreteTypes,
      inferredType: concreteTypes.size === 1 ? [...concreteTypes][0] : 'generic',
    };
  });
}

export function virtualPinDependencies(workflow: Workflow): Array<[string, string]> {
  return resolveVirtualPinGroups(workflow).flatMap((group) => (
    group.name && group.inputNodes.length === 1
      ? group.outputNodes.map((outputNode): [string, string] => [group.inputNodes[0].id, outputNode.id])
      : []
  ));
}

export function resolveVirtualPinTypes(workflow: Workflow): Map<string, DataType> {
  return new Map(resolveVirtualPinGroups(workflow).flatMap((group) => (
    [...group.inputNodes, ...group.outputNodes].map((node): [string, DataType] => [node.id, group.inferredType])
  )));
}