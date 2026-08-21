import type { NodeInspectorPlugin } from './types';
import { CameraAcquisitionInspector } from './CameraAcquisitionInspector';
import { KnnImageSegmentationInspector } from './KnnImageSegmentationInspector';

const NODE_INSPECTOR_PLUGINS: Readonly<Record<string, NodeInspectorPlugin>> = Object.freeze({
  'camera-acquisition': CameraAcquisitionInspector,
  'knn-image-segmentation': KnnImageSegmentationInspector,
});

export function getNodeInspectorPlugin(key: string | null): NodeInspectorPlugin | null {
  return key ? NODE_INSPECTOR_PLUGINS[key] ?? null : null;
}
