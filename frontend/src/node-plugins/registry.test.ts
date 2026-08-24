import { describe, expect, it } from 'vitest';
import type { NodePluginDescriptor } from './types';
import { buildNodePluginRegistry, getNodeInspectorPlugin } from './registry';

const Inspector = () => null as unknown as JSX.Element;

describe('node plugin registry', () => {
  it('builds a deterministic descriptor map and preserves inspector lookup compatibility', () => {
    const descriptors: NodePluginDescriptor[] = [
      { nodeId: 'z-node', Inspector },
      { nodeId: 'a-node', Inspector },
    ];

    const registry = buildNodePluginRegistry(descriptors);

    expect([...registry.keys()]).toEqual(['a-node', 'z-node']);
    expect(registry.get('a-node')?.Inspector).toBe(Inspector);
    expect(getNodeInspectorPlugin('camera-acquisition')).toBeTypeOf('function');
    expect(getNodeInspectorPlugin(null)).toBeNull();
  });

  it('rejects duplicate node IDs', () => {
    expect(() => buildNodePluginRegistry([
      { nodeId: 'camera-acquisition', Inspector },
      { nodeId: 'camera-acquisition', Inspector },
    ])).toThrow('Duplicate node plugin ID: camera-acquisition.');
  });

  it('rejects empty or invalid node IDs', () => {
    expect(() => buildNodePluginRegistry([{ nodeId: '', Inspector }])).toThrow('Node plugin ID is invalid.');
    expect(() => buildNodePluginRegistry([{ nodeId: 'Camera Acquisition', Inspector }])).toThrow('Node plugin ID is invalid: Camera Acquisition.');
  });
});