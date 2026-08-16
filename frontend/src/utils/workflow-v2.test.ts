import { describe, expect, it, vi } from 'vitest';
import type { AlgorithmDefinition, WorkflowPort } from '../types/workflow';
import { createNodeFromDefinition, validateConnection } from './workflow-graph';
import { addCustomPort, removeCustomPort, updateCustomPort } from './workflow-ports';

const definition: AlgorithmDefinition = {
  id: 'gaussian-blur', name: 'Gaussian blur', description: 'Blur', category: 'OpenCV tools',
  documentationGroup: 'OpenCV', availability: 'configuration-only', use: 'debug',
  inputs: [{ key: 'image', label: 'Image', direction: 'input', dataType: 'image', required: true, variadic: false }],
  outputs: [{ key: 'processed-image', label: 'Image', direction: 'output', dataType: 'image', required: true, variadic: false }],
  parameters: [], documentationReference: null, manifestVersion: 1, packageVersion: '1.0.0',
  executionTarget: 'local-cpu', inspectorKind: 'generic', customInspectorKey: null,
  controlPorts: [{ key: 'completed', label: 'Completed', direction: 'output', dataType: 'generic', required: false, variadic: false }],
};

describe('workflow v2 graph contract', () => {
  it('creates editable data ports and locked system control ports', () => {
    vi.spyOn(crypto, 'randomUUID')
      .mockReturnValueOnce('00000000-0000-4000-8000-000000000001')
      .mockReturnValueOnce('00000000-0000-4000-8000-000000000002')
      .mockReturnValueOnce('00000000-0000-4000-8000-000000000003')
      .mockReturnValueOnce('00000000-0000-4000-8000-000000000004')
      .mockReturnValueOnce('00000000-0000-4000-8000-000000000005')
      .mockReturnValueOnce('00000000-0000-4000-8000-000000000006');

    const node = createNodeFromDefinition(definition, { x: 0, y: 0 });

    expect(node.ports.filter((port) => port.channel === 'control').map((port) => port.templateKey)).toEqual([
      'trigger', 'success', 'failure', 'completed',
    ]);
    expect(node.ports.filter((port) => port.channel === 'data').every((port) => port.runtimeBinding === 'slot')).toBe(true);
  });

  it('adds editable data and control ports with explicit runtime binding', () => {
    const node = createNodeFromDefinition(definition, { x: 0, y: 0 });
    const input = addCustomPort(node, {
      templateKey: 'inspection-mask', displayLabel: 'Inspection mask', direction: 'input',
      channel: 'data', dataType: 'mask', runtimeBinding: 'slot', runtimeKey: 'image',
      passthroughInputPortId: null,
    });
    const branch = addCustomPort(input, {
      templateKey: 'retry', displayLabel: 'Retry', direction: 'output', channel: 'control',
      dataType: 'generic', runtimeBinding: 'none', runtimeKey: null, passthroughInputPortId: null,
    });

    expect(branch.ports[branch.ports.length - 2]).toMatchObject({
      templateKey: 'inspection-mask', channel: 'data', origin: 'custom', runtimeKey: 'image',
    });
    expect(branch.ports[branch.ports.length - 1]).toMatchObject({
      templateKey: 'retry', channel: 'control', origin: 'custom', runtimeBinding: 'none',
    });
  });

  it('locks system ports while custom ports can be changed and removed', () => {
    const node = createNodeFromDefinition(definition, { x: 0, y: 0 });
    const system = node.ports.find((port) => port.origin === 'system')!;
    const custom = addCustomPort(node, {
      templateKey: 'custom-output', displayLabel: 'Custom output', direction: 'output',
      channel: 'data', dataType: 'image', runtimeBinding: 'passthrough', runtimeKey: null,
      passthroughInputPortId: node.ports.find((port) => port.direction === 'input')!.id,
    });
    const customPort = custom.ports[custom.ports.length - 1] as WorkflowPort;

    expect(() => updateCustomPort(node, system.id, { displayLabel: 'Changed' })).toThrow(/system port/i);
    expect(() => removeCustomPort(node, system.id)).toThrow(/system port/i);
    const updated = updateCustomPort(custom, customPort.id, { displayLabel: 'Forwarded image' });
    expect(updated.ports[updated.ports.length - 1]?.displayLabel).toBe('Forwarded image');
    expect(removeCustomPort(custom, customPort.id).ports).not.toContainEqual(customPort);
  });

  it('rejects duplicate keys and invalid passthrough bindings', () => {
    const node = createNodeFromDefinition(definition, { x: 0, y: 0 });

    expect(() => addCustomPort(node, {
      templateKey: 'trigger', displayLabel: 'Duplicate', direction: 'input', channel: 'control',
      dataType: 'generic', runtimeBinding: 'none', runtimeKey: null, passthroughInputPortId: null,
    })).toThrow(/unique/i);
    expect(() => addCustomPort(node, {
      templateKey: 'forward', displayLabel: 'Forward', direction: 'output', channel: 'data',
      dataType: 'image', runtimeBinding: 'passthrough', runtimeKey: null, passthroughInputPortId: 'missing',
    })).toThrow(/passthrough/i);
  });

  it('accepts a bounded feedback control edge and rejects an unbounded one', () => {
    const first = createNodeFromDefinition(definition, { x: 0, y: 0 });
    const second = createNodeFromDefinition(definition, { x: 200, y: 0 });
    const success = (node: typeof first) => node.ports.find((port) => port.templateKey === 'success')!;
    const trigger = (node: typeof first) => node.ports.find((port) => port.templateKey === 'trigger')!;
    const base = {
      recipeSlug: 'flow', recipeName: 'Flow', version: 2, revision: 0, updatedAt: new Date().toISOString(),
      nodes: [first, second], executionOrder: [first.id, second.id],
      migrationNotices: [],
      connections: [{
        id: crypto.randomUUID(), sourceNodeId: first.id, sourcePortId: success(first).id,
        targetNodeId: second.id, targetPortId: trigger(second).id, kind: 'control' as const, maxTraversals: null,
      }],
    };
    const draft = {
      sourceNodeId: second.id, sourcePortId: success(second).id,
      targetNodeId: first.id, targetPortId: trigger(first).id, kind: 'control' as const, maxTraversals: 3,
    };

    expect(validateConnection(base, draft)).toBeNull();
    expect(validateConnection(base, { ...draft, maxTraversals: null })?.code).toBe('unbounded-control-cycle');
  });
});