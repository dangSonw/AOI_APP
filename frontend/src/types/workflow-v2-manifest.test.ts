import { describe, expect, it } from 'vitest';
import type { AlgorithmDefinition } from './workflow';

describe('workflow manifest v2 frontend contract', () => {
  it('accepts optional typed actions and artifact contracts while preserving v1 defaults', () => {
    const definition: AlgorithmDefinition = {
      id: 'svm-image-classifier', name: 'SVM image classifier', description: 'Train SVM',
      category: 'Classification', documentationGroup: 'Classical machine learning', availability: 'configuration-only',
      use: 'debug', inputs: [], outputs: [], parameters: [], documentationReference: null,
      manifestVersion: 2, packageVersion: '1.0.0', executionTarget: 'local-cpu',
      inspectorKind: 'custom', customInspectorKey: 'svm-image-classifier',
      capabilities: ['configure', 'train'],
      actions: {
        train: { datasetInputs: ['training-dataset'], executionTargets: ['local-cpu'], cancellable: true },
      },
      artifactContracts: {
        outputs: [{ key: 'model', schema: 'aoi.model.v1' }],
      },
    };

    expect(definition.actions?.train.datasetInputs).toEqual(['training-dataset']);
    expect(definition.artifactContracts?.outputs[0].schema).toBe('aoi.model.v1');
  });
});