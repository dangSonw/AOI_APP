import { useState } from 'react';
import { TrainingJobPanel } from '../../components/workflow/TrainingJobPanel';
import { useTrainingJob } from '../../hooks/use-training-job';
import type { TrainingJobCreate } from '../../types/training-job';
import type { AlgorithmDefinition, ParameterValue, WorkflowNode } from '../../types/workflow';
import type { NodeInspectorPluginProps } from '../types';

interface SvmTrainingForm {
  experimentId: string;
  trainingDatasetId: string;
  trainingVersion: string;
  testDatasetId: string;
  testVersion: string;
}

const IMMUTABLE_VERSION = /^sha256:[0-9a-f]{64}$/;

export function validateSvmHogParameters(parameters: Readonly<Record<string, ParameterValue>>): string {
  const blockWidth = Number(parameters.hogBlockWidth);
  const blockHeight = Number(parameters.hogBlockHeight);
  const strideX = Number(parameters.hogBlockStrideX);
  const strideY = Number(parameters.hogBlockStrideY);
  const cellWidth = Number(parameters.hogCellWidth);
  const cellHeight = Number(parameters.hogCellHeight);
  const windowWidth = Number(parameters.hogWindowWidth);
  const windowHeight = Number(parameters.hogWindowHeight);
  if ([blockWidth, blockHeight, strideX, strideY, cellWidth, cellHeight, windowWidth, windowHeight].some((value) => !Number.isInteger(value) || value < 1)) {
    return 'HOG dimensions must be positive integers.';
  }
  if (blockWidth % cellWidth || blockHeight % cellHeight) return 'HOG block dimensions must be divisible by cell dimensions.';
  if (strideX % cellWidth || strideY % cellHeight) return 'HOG stride must be divisible by cell dimensions.';
  if ((windowWidth - blockWidth) % strideX || (windowHeight - blockHeight) % strideY) return 'HOG window geometry must be divisible by block stride.';
  return '';
}

export function buildSvmTrainingRequest(
  node: WorkflowNode,
  definition: AlgorithmDefinition,
  form: SvmTrainingForm,
): TrainingJobCreate {
  return {
    experimentId: form.experimentId,
    recipeSlug: '',
    workflowRevision: 1,
    nodeInstanceId: node.id,
    nodeId: definition.id,
    nodePackageVersion: definition.packageVersion,
    actionName: 'train',
    executionTarget: 'local-cpu',
    datasetBindings: {
      'training-dataset': { datasetId: form.trainingDatasetId, version: form.trainingVersion },
      'test-dataset': { datasetId: form.testDatasetId, version: form.testVersion },
    },
    parameters: { ...node.parameters },
    randomSeeds: { python: Number(node.parameters.randomSeed ?? 42), numpy: Number(node.parameters.randomSeed ?? 42) },
    parentRunId: null,
  };
}

export function SvmImageClassifierInspector({ node, definition, updateParameter, context }: NodeInspectorPluginProps) {
  const [form, setForm] = useState<SvmTrainingForm>({ experimentId: '', trainingDatasetId: '', trainingVersion: '', testDatasetId: '', testVersion: '' });
  const [formError, setFormError] = useState('');
  const training = context?.training;
  const jobState = useTrainingJob({
    create: async (request) => {
      if (!training) throw new Error('Training requires an authenticated workflow session.');
      const { recipeSlug: _recipeSlug, workflowRevision: _workflowRevision, nodeInstanceId: _nodeInstanceId, ...intent } = request;
      return training.create(intent);
    },
    read: async (runId) => {
      if (!training) throw new Error('Training requires an authenticated workflow session.');
      return training.read(runId);
    },
    cancel: async (runId) => {
      if (!training) throw new Error('Training requires an authenticated workflow session.');
      return training.cancel(runId);
    },
  });
  const updateForm = (key: keyof SvmTrainingForm, value: string) => setForm((current) => ({ ...current, [key]: value }));
  const numberField = (key: string, label: string, minimum = 1) => (
    <label className="workflow-field"><span>{label}</span><input type="number" min={minimum} value={Number(node.parameters[key])} onChange={(event) => updateParameter(key, Number(event.target.value))} /></label>
  );
  const hogError = validateSvmHogParameters(node.parameters);
  const start = () => {
    if (!context || !training) { setFormError('Training requires an authenticated workflow session.'); return; }
    if (!form.experimentId || !form.trainingDatasetId || !form.testDatasetId) { setFormError('Experiment and both dataset IDs are required.'); return; }
    if (!IMMUTABLE_VERSION.test(form.trainingVersion) || !IMMUTABLE_VERSION.test(form.testVersion)) { setFormError('Dataset versions must use immutable sha256 identifiers.'); return; }
    if (hogError) { setFormError(hogError); return; }
    setFormError('');
    const request = buildSvmTrainingRequest(node, definition, form);
    void jobState.start({ ...request, recipeSlug: context.recipeSlug, workflowRevision: context.workflowRevision, nodeInstanceId: context.nodeInstanceId }).catch(() => undefined);
  };

  return (
    <div data-inspector-content="custom" className="svm-plugin">
      <section className="workflow-inspector__section"><h3>Dataset</h3>
        <label className="workflow-field"><span>Experiment ID</span><input value={form.experimentId} onChange={(event) => updateForm('experimentId', event.target.value)} /></label>
        <label className="workflow-field"><span>Training dataset ID</span><input value={form.trainingDatasetId} onChange={(event) => updateForm('trainingDatasetId', event.target.value)} /></label>
        <label className="workflow-field"><span>Training dataset version</span><input placeholder="sha256:…" value={form.trainingVersion} onChange={(event) => updateForm('trainingVersion', event.target.value)} /></label>
        <label className="workflow-field"><span>Test dataset ID</span><input value={form.testDatasetId} onChange={(event) => updateForm('testDatasetId', event.target.value)} /></label>
        <label className="workflow-field"><span>Test dataset version</span><input placeholder="sha256:…" value={form.testVersion} onChange={(event) => updateForm('testVersion', event.target.value)} /></label>
        <p className="workflow-hint"><strong>Label mapping:</strong> class names and contiguous IDs come from each immutable dataset version.</p>
      </section>
      <section className="workflow-inspector__section"><h3>Feature extraction</h3>
        <div className="svm-plugin__grid">{numberField('imageWidth', 'Image width')}{numberField('imageHeight', 'Image height')}{numberField('hogBlockWidth', 'HOG block width')}{numberField('hogBlockHeight', 'HOG block height')}{numberField('hogBlockStrideX', 'HOG stride X')}{numberField('hogBlockStrideY', 'HOG stride Y')}{numberField('hogCellWidth', 'HOG cell width')}{numberField('hogCellHeight', 'HOG cell height')}{numberField('hogBins', 'HOG bins')}</div>
        {hogError && <p className="workflow-field-error" role="alert">{hogError}</p>}
      </section>
      <section className="workflow-inspector__section"><h3>Model</h3>
        <label className="workflow-field"><span>Kernel</span><select value={String(node.parameters.kernel)} onChange={(event) => updateParameter('kernel', event.target.value)}><option value="linear">Linear</option><option value="rbf">RBF</option><option value="poly">Polynomial</option><option value="sigmoid">Sigmoid</option></select></label>
        {numberField('c', 'C', 0.000001)}
        {node.parameters.kernel !== 'linear' && <label className="workflow-field"><span>Gamma</span><input value={String(node.parameters.gamma)} onChange={(event) => updateParameter('gamma', event.target.value)} /></label>}
        {node.parameters.kernel === 'poly' && numberField('degree', 'Polynomial degree')}
        <label className="workflow-field"><span>Use StandardScaler</span><input type="checkbox" checked={Boolean(node.parameters.useScaler)} onChange={(event) => updateParameter('useScaler', event.target.checked)} /></label>
      </section>
      <section className="workflow-inspector__section"><h3>Training</h3><p className="workflow-hint">The server validates immutable datasets and executes HOG/SVC behavior inside the node package.</p></section>
      <TrainingJobPanel job={jobState.job} error={formError || jobState.error} isStarting={jobState.isStarting} isCancelling={jobState.isCancelling} onStart={start} onCancel={() => void jobState.cancel()} onOpenRun={(runId) => training?.openRun(runId)} />
      <section className="workflow-inspector__section"><h3>Results</h3><p className="workflow-hint">Completed metrics and typed artifacts are available in Research.</p></section>
    </div>
  );
}