import type { NodeInspectorPlugin } from './types';
import { CameraAcquisitionInspector } from './CameraAcquisitionInspector';

const NODE_INSPECTOR_PLUGINS: Readonly<Record<string, NodeInspectorPlugin>> = Object.freeze({
  'camera-acquisition': CameraAcquisitionInspector,
});

export function getNodeInspectorPlugin(key: string | null): NodeInspectorPlugin | null {
  return key ? NODE_INSPECTOR_PLUGINS[key] ?? null : null;
}
