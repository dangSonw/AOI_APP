import type { NodeInspectorPlugin, NodePluginDescriptor } from './types';
import type { AlgorithmDefinition } from '../types/workflow';
import { discoverNodePluginDescriptors, validateNodePluginCatalog } from './discovery';

const NODE_PLUGIN_ID_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export function buildNodePluginRegistry(
  descriptors: readonly NodePluginDescriptor[],
): ReadonlyMap<string, NodePluginDescriptor> {
  const registry = new Map<string, NodePluginDescriptor>();
  for (const descriptor of [...descriptors].sort((left, right) => left.nodeId.localeCompare(right.nodeId))) {
    if (!descriptor.nodeId || !NODE_PLUGIN_ID_PATTERN.test(descriptor.nodeId)) {
      throw new Error(descriptor.nodeId ? `Node plugin ID is invalid: ${descriptor.nodeId}.` : 'Node plugin ID is invalid.');
    }
    if (registry.has(descriptor.nodeId)) throw new Error(`Duplicate node plugin ID: ${descriptor.nodeId}.`);
    registry.set(descriptor.nodeId, Object.freeze({ ...descriptor }));
  }
  return registry;
}

const DISCOVERED_NODE_PLUGINS = discoverNodePluginDescriptors(
  import.meta.glob('./*/index.ts', { eager: true }),
);
const NODE_PLUGIN_REGISTRY = buildNodePluginRegistry(DISCOVERED_NODE_PLUGINS);

export function validateRegisteredNodePlugins(definitions: readonly AlgorithmDefinition[]): void {
  validateNodePluginCatalog([...NODE_PLUGIN_REGISTRY.values()], definitions);
}

export function getNodeInspectorPlugin(key: string | null): NodeInspectorPlugin | null {
  return key ? NODE_PLUGIN_REGISTRY.get(key)?.Inspector ?? null : null;
}
