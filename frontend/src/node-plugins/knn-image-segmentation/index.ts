import type { NodePluginDescriptor } from '../types';
import { KnnImageSegmentationInspector } from './inspector';

export const knnImageSegmentationPlugin: NodePluginDescriptor = Object.freeze({
  nodeId: 'knn-image-segmentation',
  Inspector: KnnImageSegmentationInspector,
});