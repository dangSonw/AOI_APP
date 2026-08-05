import type {
  AlgorithmDefinition,
  ConnectionDraft,
  ParameterDefinition,
  ParameterValue,
  ValidationIssue,
  Workflow,
  WorkflowConnection,
  WorkflowNode,
  WorkflowPoint,
  WorkflowPort,
} from '../types/workflow';


function issue(code: ValidationIssue['code'], message: string, context: Partial<ValidationIssue> = {}): ValidationIssue {
  return { code, message, ...context };
}

function findPort(workflow: Workflow, nodeId: string, portId: string): WorkflowPort | undefined {
  return workflow.nodes.find((node) => node.id === nodeId)?.ports.find((port) => port.id === portId);
}

function createsCycle(workflow: Workflow, sourceNodeId: string, targetNodeId: string): boolean {
  const dependents = new Map<string, string[]>();
  for (const connection of workflow.connections) {
    const targets = dependents.get(connection.sourceNodeId) ?? [];
    targets.push(connection.targetNodeId);
    dependents.set(connection.sourceNodeId, targets);
  }
  const stack = [targetNodeId];
  const visited = new Set<string>();
  while (stack.length > 0) {
    const current = stack.pop();
    if (!current || visited.has(current)) {
      continue;
    }
    if (current === sourceNodeId) {
      return true;
    }
    visited.add(current);
    stack.push(...(dependents.get(current) ?? []));
  }
  return false;
}

export function createNodeFromDefinition(
  definition: AlgorithmDefinition,
  position: WorkflowPoint,
): WorkflowNode {
  const nodeId = crypto.randomUUID();
  const ports = [...definition.inputs, ...definition.outputs].map<WorkflowPort>((port) => ({
    id: crypto.randomUUID(),
    templateKey: port.key,
    direction: port.direction,
    dataType: port.dataType,
    displayLabel: port.label,
    required: port.required,
    variadic: port.variadic,
    variadicInstanceIndex: port.variadic ? 0 : null,
  }));
  return {
    id: nodeId,
    algorithmId: definition.id,
    displayName: definition.name,
    position,
    parameters: Object.fromEntries(definition.parameters.map((parameter) => [parameter.key, parameter.defaultValue])),
    ports,
  };
}

export function validateConnection(
  workflow: Workflow,
  connection: ConnectionDraft,
): ValidationIssue | null {
  const sourceNode = workflow.nodes.find((node) => node.id === connection.sourceNodeId);
  const targetNode = workflow.nodes.find((node) => node.id === connection.targetNodeId);
  if (!sourceNode || !targetNode) {
    return issue('unknown-node', 'Both connection nodes must exist.');
  }
  const sourcePort = findPort(workflow, sourceNode.id, connection.sourcePortId);
  const targetPort = findPort(workflow, targetNode.id, connection.targetPortId);
  if (!sourcePort || !targetPort || sourcePort.direction !== 'output' || targetPort.direction !== 'input') {
    return issue('unknown-port', 'Connect an output port to an input port.');
  }
  if (sourceNode.id === targetNode.id) {
    return issue('self-loop', 'A node cannot connect to itself.');
  }
  if (sourcePort.dataType !== targetPort.dataType) {
    return issue('type-mismatch', `Connect ${sourcePort.dataType} only to ${sourcePort.dataType}.`);
  }
  if (workflow.connections.some((candidate) =>
    candidate.sourceNodeId === connection.sourceNodeId
    && candidate.sourcePortId === connection.sourcePortId
    && candidate.targetNodeId === connection.targetNodeId
    && candidate.targetPortId === connection.targetPortId)) {
    return issue('duplicate-connection', 'These ports are already connected.');
  }
  if (!targetPort.variadic && workflow.connections.some((candidate) =>
    candidate.targetNodeId === connection.targetNodeId && candidate.targetPortId === connection.targetPortId)) {
    return issue('input-already-connected', 'The target input already has a connection.');
  }
  if (createsCycle(workflow, sourceNode.id, targetNode.id)) {
    return issue('cycle', 'This connection would create a cycle.');
  }
  return null;
}

export function stableTopologicalOrder(workflow: Workflow, preferredOrder = workflow.executionOrder): string[] {
  const nodeIds = workflow.nodes.map((node) => node.id);
  const nodeSet = new Set(nodeIds);
  const rank = new Map(preferredOrder.map((nodeId, index) => [nodeId, index]));
  const fallback = new Map(nodeIds.map((nodeId, index) => [nodeId, index]));
  const indegree = new Map(nodeIds.map((nodeId) => [nodeId, 0]));
  const dependents = new Map<string, Set<string>>();
  for (const connection of workflow.connections) {
    if (!nodeSet.has(connection.sourceNodeId) || !nodeSet.has(connection.targetNodeId)) {
      continue;
    }
    const targets = dependents.get(connection.sourceNodeId) ?? new Set<string>();
    if (!targets.has(connection.targetNodeId)) {
      targets.add(connection.targetNodeId);
      dependents.set(connection.sourceNodeId, targets);
      indegree.set(connection.targetNodeId, (indegree.get(connection.targetNodeId) ?? 0) + 1);
    }
  }
  const orderKey = (nodeId: string) => rank.get(nodeId) ?? preferredOrder.length + (fallback.get(nodeId) ?? 0);
  const ready = nodeIds.filter((nodeId) => indegree.get(nodeId) === 0).sort((left, right) => orderKey(left) - orderKey(right));
  const result: string[] = [];
  while (ready.length > 0) {
    const current = ready.shift();
    if (!current) {
      break;
    }
    result.push(current);
    for (const target of [...(dependents.get(current) ?? [])].sort((left, right) => orderKey(left) - orderKey(right))) {
      indegree.set(target, (indegree.get(target) ?? 0) - 1);
      if (indegree.get(target) === 0) {
        ready.push(target);
        ready.sort((left, right) => orderKey(left) - orderKey(right));
      }
    }
  }
  return result.length === nodeIds.length ? result : [];
}

function parameterIsValid(definition: ParameterDefinition, value: ParameterValue | undefined): boolean {
  if (value === undefined) {
    return !definition.required;
  }
  if (definition.kind === 'boolean' && typeof value !== 'boolean') return false;
  if (definition.kind === 'integer' && (!Number.isInteger(value) || typeof value !== 'number')) return false;
  if (definition.kind === 'number' && (typeof value !== 'number' || !Number.isFinite(value))) return false;
  if ((definition.kind === 'text' || definition.kind === 'select') && typeof value !== 'string') return false;
  if (typeof value === 'number' && definition.minimum !== null && value < definition.minimum) return false;
  if (typeof value === 'number' && definition.maximum !== null && value > definition.maximum) return false;
  if (definition.kind === 'select' && !definition.options.includes(value)) return false;
  return true;
}

export function validateDraft(workflow: Workflow, catalog: AlgorithmDefinition[]): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const definitions = new Map(catalog.map((definition) => [definition.id, definition]));
  const allIds = [
    ...workflow.nodes.map((node) => node.id),
    ...workflow.nodes.flatMap((node) => node.ports.map((port) => port.id)),
    ...workflow.connections.map((connection) => connection.id),
  ];
  const seenIds = new Set<string>();
  for (const id of allIds) {
    if (seenIds.has(id)) issues.push(issue('duplicate-id', 'Node, port, and connection IDs must be unique.'));
    seenIds.add(id);
  }
  for (const node of workflow.nodes) {
    const definition = definitions.get(node.algorithmId);
    if (!definition) {
      issues.push(issue('unknown-algorithm', 'The node algorithm is not available.', { nodeId: node.id }));
      continue;
    }
    for (const parameter of definition.parameters) {
      if (!parameterIsValid(parameter, node.parameters[parameter.key])) {
        issues.push(issue('invalid-parameter', `${parameter.label} is invalid.`, { nodeId: node.id }));
      }
    }
    for (const port of node.ports.filter((candidate) => candidate.direction === 'input' && candidate.required)) {
      if (!workflow.connections.some((connection) => connection.targetNodeId === node.id && connection.targetPortId === port.id)) {
        issues.push(issue('missing-required-input', `${port.displayLabel} requires a connection.`, { nodeId: node.id, portId: port.id }));
      }
    }
  }
  for (const connection of workflow.connections) {
    const connectionIssue = validateConnection(
      { ...workflow, connections: workflow.connections.filter((candidate) => candidate.id !== connection.id) },
      connection,
    );
    if (connectionIssue) issues.push({ ...connectionIssue, connectionId: connection.id });
  }
  const expected = workflow.nodes.map((node) => node.id);
  if (workflow.executionOrder.length !== expected.length || new Set(workflow.executionOrder).size !== expected.length
    || expected.some((nodeId) => !workflow.executionOrder.includes(nodeId))) {
    issues.push(issue('execution-order-mismatch', 'Execution order must contain every node exactly once.'));
  } else {
    const positions = new Map(workflow.executionOrder.map((nodeId, index) => [nodeId, index]));
    for (const connection of workflow.connections) {
      if ((positions.get(connection.sourceNodeId) ?? Infinity) >= (positions.get(connection.targetNodeId) ?? -1)) {
        issues.push(issue('dependency-order', 'Move dependencies before their consumers.', { connectionId: connection.id }));
      }
    }
  }
  if (workflow.nodes.length > 0 && stableTopologicalOrder(workflow).length === 0) {
    issues.push(issue('cycle', 'The workflow must not contain a cycle.'));
  }
  return issues;
}

export function moveExecutionNode(order: string[], nodeId: string, offset: -1 | 1): string[] {
  const currentIndex = order.indexOf(nodeId);
  const targetIndex = currentIndex + offset;
  if (currentIndex < 0 || targetIndex < 0 || targetIndex >= order.length) {
    return order;
  }
  const nextOrder = [...order];
  [nextOrder[currentIndex], nextOrder[targetIndex]] = [nextOrder[targetIndex], nextOrder[currentIndex]];
  return nextOrder;
}

export function filterCatalog(catalog: AlgorithmDefinition[], query: string): AlgorithmDefinition[] {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  if (!normalizedQuery) return catalog;
  return catalog.filter((definition) => [
    definition.id,
    definition.name,
    definition.description,
    definition.category,
    definition.documentationGroup,
  ].some((value) => value.toLocaleLowerCase().includes(normalizedQuery)));
}

export function isWorkflowDirty(saved: Workflow | null, draft: Workflow | null): boolean {
  if (!saved || !draft) return saved !== draft;
  return JSON.stringify(saved) !== JSON.stringify(draft);
}

export function addConnection(workflow: Workflow, connection: ConnectionDraft): Workflow {
  const nextConnection: WorkflowConnection = { id: crypto.randomUUID(), ...connection };
  return { ...workflow, connections: [...workflow.connections, nextConnection] };
}