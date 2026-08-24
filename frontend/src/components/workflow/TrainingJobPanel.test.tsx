import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { TrainingJobPanel, createTrainingJobActions } from './TrainingJobPanel';
import type { TrainingJob } from '../../types/training-job';

const runningJob: TrainingJob = {
  id: 'run-01', experimentId: 'experiment-01', status: 'training', executionTarget: 'local-cpu',
  codeRevision: 'server-revision', nodeId: 'fake-trainer', nodeInstanceId: 'node-01',
  nodePackageVersion: '1.0.0', actionName: 'train', workflowRevision: 1,
  datasetBindings: {}, parameters: {}, randomSeeds: {}, environment: {},
  progress: { stage: 'training', processedUnits: 3, totalUnits: 10, fraction: 0.3, message: 'Extracting features' },
  metrics: {}, outputArtifacts: [], error: null, parentRunId: null,
  createdAt: '2026-08-24T00:00:00Z', completedAt: null,
};

describe('TrainingJobPanel', () => {
  it('renders accessible generic progress, status, error, and actions without algorithm fields', () => {
    const markup = renderToStaticMarkup(
      <TrainingJobPanel
        job={runningJob}
        error=""
        isStarting={false}
        isCancelling={false}
        onStart={vi.fn()}
        onCancel={vi.fn()}
        onOpenRun={vi.fn()}
      />,
    );

    expect(markup).toContain('Training job');
    expect(markup).toContain('role="progressbar"');
    expect(markup).toContain('aria-valuenow="30"');
    expect(markup).toContain('Extracting features');
    expect(markup).toContain('Cancel job');
    expect(markup).toContain('Open run');
    expect(markup).not.toContain('kernel');
    expect(markup).not.toContain('HOG');
  });

  it('prevents duplicate starts while one create request is pending', async () => {
    let resolveStart: ((job: TrainingJob) => void) | undefined;
    const start = vi.fn(() => new Promise<TrainingJob>((resolve) => { resolveStart = resolve; }));
    const actions = createTrainingJobActions(start);

    const first = actions.start();
    const second = actions.start();

    expect(start).toHaveBeenCalledOnce();
    expect(second).toBe(first);
    resolveStart?.(runningJob);
    await first;
  });

  it('announces request failures and allows a retry when no job is active', () => {
    const markup = renderToStaticMarkup(
      <TrainingJobPanel
        job={null}
        error="Training service unavailable."
        isStarting={false}
        isCancelling={false}
        onStart={vi.fn()}
        onCancel={vi.fn()}
        onOpenRun={vi.fn()}
      />,
    );

    expect(markup).toContain('role="alert"');
    expect(markup).toContain('Training service unavailable.');
    expect(markup).toContain('Start job');
  });
});