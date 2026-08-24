import type { NodePluginDescriptor } from '../types';
import { SvmImageClassifierInspector } from './inspector';
import { SvmImageClassifierResultView } from './result-view';

export const svmImageClassifierPlugin: NodePluginDescriptor = Object.freeze({
  nodeId: 'svm-image-classifier',
  Inspector: SvmImageClassifierInspector,
  ResultView: SvmImageClassifierResultView,
});