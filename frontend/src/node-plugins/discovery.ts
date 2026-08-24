import type { AlgorithmDefinition } from '../types/workflow';
import type { NodePluginDescriptor } from './types';

type PluginModule = Readonly<Record<string, unknown>>;
type PluginModuleMap = Readonly<Record<string, PluginModule>>;

function isNodePluginDescriptor(value: unknown): value is NodePluginDescriptor {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<NodePluginDescriptor>;
  return typeof candidate.nodeId === 'string'
    && (candidate.Inspector === undefined || typeof candidate.Inspector === 'function')
    && (candidate.ResultView === undefined || typeof candidate.ResultView === 'function')
    && (candidate.Preview === undefined || typeof candidate.Preview === 'function');
}

export function discoverNodePluginDescriptors(modules: PluginModuleMap): NodePluginDescriptor[] {
  return Object.keys(modules).sort().map((path) => {
    const descriptors = Object.values(modules[path]).filter(isNodePluginDescriptor);
    if (descriptors.length !== 1) {
      throw new Error(`Node plugin module ${path} must export exactly one descriptor.`);
    }
    return descriptors[0];
  });
}

export function validateNodePluginCatalog(
  descriptors: readonly NodePluginDescriptor[],
  definitions: readonly AlgorithmDefinition[],
): void {
  const pluginIds = new Set(descriptors.map((descriptor) => descriptor.nodeId));
  const manifestKeys = new Set(definitions.flatMap((definition) => (
    definition.inspectorKind === 'custom' && definition.customInspectorKey
      ? [definition.customInspectorKey]
      : []
  )));
  for (const pluginId of [...pluginIds].sort()) {
    if (!manifestKeys.has(pluginId)) {
      throw new Error(`Node plugin ${pluginId} does not match a manifest custom inspector key.`);
    }
  }
  for (const manifestKey of [...manifestKeys].sort()) {
    if (!pluginIds.has(manifestKey)) {
      throw new Error(`Manifest custom inspector key ${manifestKey} does not have a frontend plugin.`);
    }
  }
}