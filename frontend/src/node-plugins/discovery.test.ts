import { describe, expect, it } from 'vitest';
import type { AlgorithmDefinition } from '../types/workflow';
import type { NodePluginDescriptor } from './types';
import { discoverNodePluginDescriptors, validateNodePluginCatalog } from './discovery';

const Inspector = () => null as unknown as JSX.Element;

function definition(id: string, customInspectorKey: string | null): AlgorithmDefinition {
  return {
    id, name: id, description: id, category: 'Test', documentationGroup: 'Test',
    availability: 'configuration-only', use: 'test', inputs: [], outputs: [], parameters: [],
    documentationReference: null, manifestVersion: 1, packageVersion: '1.0.0', executionTarget: 'local-cpu',
    inspectorKind: customInspectorKey ? 'custom' : 'generic', customInspectorKey,
  };
}

describe('node plugin discovery', () => {
  it('discovers one descriptor per module in deterministic path order', () => {
    const descriptors = discoverNodePluginDescriptors({
      './z-node/index.ts': { zNodePlugin: { nodeId: 'z-node', Inspector } satisfies NodePluginDescriptor },
      './a-node/index.ts': { aNodePlugin: { nodeId: 'a-node', Inspector } satisfies NodePluginDescriptor },
    });

    expect(descriptors.map((descriptor) => descriptor.nodeId)).toEqual(['a-node', 'z-node']);
  });

  it('rejects modules with no descriptor or multiple descriptors', () => {
    expect(() => discoverNodePluginDescriptors({ './empty/index.ts': { value: 1 } }))
      .toThrow('Node plugin module ./empty/index.ts must export exactly one descriptor.');
    expect(() => discoverNodePluginDescriptors({
      './duplicate/index.ts': {
        first: { nodeId: 'first-node', Inspector },
        second: { nodeId: 'second-node', Inspector },
      },
    })).toThrow('Node plugin module ./duplicate/index.ts must export exactly one descriptor.');
  });

  it('rejects a plugin without a manifest custom key', () => {
    expect(() => validateNodePluginCatalog(
      [{ nodeId: 'orphan-plugin', Inspector }],
      [definition('camera-capture', 'camera-acquisition')],
    )).toThrow('Node plugin orphan-plugin does not match a manifest custom inspector key.');
  });

  it('rejects a manifest custom key without a plugin', () => {
    expect(() => validateNodePluginCatalog(
      [{ nodeId: 'camera-acquisition', Inspector }],
      [definition('camera-capture', 'camera-acquisition'), definition('knn-image-segmentation', 'knn-image-segmentation')],
    )).toThrow('Manifest custom inspector key knn-image-segmentation does not have a frontend plugin.');
  });
});