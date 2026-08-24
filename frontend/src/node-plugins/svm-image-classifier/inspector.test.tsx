import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { NodePluginPlatformContext } from '../types';
import type { AlgorithmDefinition, WorkflowNode } from '../../types/workflow';
import { SvmImageClassifierInspector, buildSvmTrainingRequest, validateSvmHogParameters } from './inspector';
import { SvmImageClassifierResultView } from './result-view';

const node: WorkflowNode = { id: 'node-svm', algorithmId: 'svm-image-classifier', displayName: 'SVM', position: { x: 0, y: 0 }, parameters: { imageWidth: 128, imageHeight: 128, hogWindowWidth: 128, hogWindowHeight: 128, hogBlockWidth: 16, hogBlockHeight: 16, hogBlockStrideX: 8, hogBlockStrideY: 8, hogCellWidth: 8, hogCellHeight: 8, hogBins: 9, useScaler: true, kernel: 'rbf', c: 10, gamma: 'scale', degree: 3, classWeight: 'none', probability: false, invalidImagePolicy: 'fail', maxSamples: 10000, maxImagePixels: 16777216, randomSeed: 42 }, ports: [] };
const definition = { id: 'svm-image-classifier', packageVersion: '1.0.0', executionTarget: 'local-cpu' } as AlgorithmDefinition;
const context: NodePluginPlatformContext = { accessToken: 'token', recipeSlug: 'recipe', workflowRevision: 4, nodeInstanceId: 'node-svm', training: { create: vi.fn(), read: vi.fn(), cancel: vi.fn(), openRun: vi.fn() } };

describe('SVM image classifier plugin', () => {
  it('renders dataset, feature extraction, model, training, and results sections with shared job panel', () => {
    const markup = renderToStaticMarkup(<SvmImageClassifierInspector node={node} definition={definition} updateParameter={vi.fn()} context={context} />);
    for (const heading of ['Dataset', 'Feature extraction', 'Model', 'Training', 'Results']) expect(markup).toContain(`>${heading}<`);
    expect(markup).toContain('Training dataset version');
    expect(markup).toContain('sha256:');
    expect(markup).toContain('Label mapping');
    expect(markup).toContain('Training job');
    expect(markup).toContain('Gamma');
    expect(markup).not.toContain('host path');
  });

  it('validates HOG geometry and builds only the declared immutable training intent', () => {
    expect(validateSvmHogParameters(node.parameters)).toBe('');
    expect(validateSvmHogParameters({ ...node.parameters, hogBlockWidth: 15 })).toContain('divisible');
    const request = buildSvmTrainingRequest(node, definition, { experimentId: 'animals', trainingDatasetId: 'animals-train', trainingVersion: `sha256:${'a'.repeat(64)}`, testDatasetId: 'animals-test', testVersion: `sha256:${'b'.repeat(64)}` });
    expect(request.nodeId).toBe('svm-image-classifier');
    expect(request.datasetBindings['training-dataset'].version).toMatch(/^sha256:/);
    expect(request.parameters).toEqual(node.parameters);
    expect(request).not.toHaveProperty('metrics');
    expect(request).not.toHaveProperty('artifacts');
  });

  it('renders accessible metric, report, and confusion text fallbacks', () => {
    const markup = renderToStaticMarkup(<SvmImageClassifierResultView node={node} definition={definition} context={context} result={{ runId: 'run-01', metrics: { accuracy: 0.95 }, report: { rows: [{ label: 'cats', precision: 1, recall: 0.9 }] }, confusionMatrix: { labels: ['cats', 'dogs'], matrix: [[2, 0], [1, 1]] } }} />);
    expect(markup).toContain('Accuracy'); expect(markup).toContain('95.0%');
    expect(markup).toContain('cats'); expect(markup).toContain('2');
    expect(markup).toContain('<table'); expect(markup).toContain('Open run');
  });
});