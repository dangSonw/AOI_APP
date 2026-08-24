import type { NodePluginDescriptor } from '../types';
import { CameraAcquisitionInspector } from './inspector';

export const cameraAcquisitionPlugin: NodePluginDescriptor = Object.freeze({
  nodeId: 'camera-acquisition',
  Inspector: CameraAcquisitionInspector,
});