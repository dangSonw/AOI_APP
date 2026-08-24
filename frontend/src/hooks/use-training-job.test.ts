import { afterEach, describe, expect, it, vi } from 'vitest';
import { createTrainingJobPoller } from './use-training-job';
import type { TrainingJob } from '../types/training-job';

const job = (status: TrainingJob['status']): TrainingJob => ({
  id: 'run-01', experimentId: 'experiment-01', status, executionTarget: 'local-cpu',
  codeRevision: 'server-revision', nodeId: 'fake-trainer', nodeInstanceId: 'node-01',
  nodePackageVersion: '1.0.0', actionName: 'train', workflowRevision: 1,
  datasetBindings: {}, parameters: {}, randomSeeds: {}, environment: {}, progress: null,
  metrics: {}, outputArtifacts: [], error: null, parentRunId: null,
  createdAt: '2026-08-24T00:00:00Z', completedAt: null,
});

afterEach(() => {
  vi.useRealTimers();
});

describe('training job poller', () => {
  it('starts immediately, polls at a bounded interval, and stops on terminal state', async () => {
    vi.useFakeTimers();
    const read = vi.fn()
      .mockResolvedValueOnce(job('training'))
      .mockResolvedValueOnce(job('completed'));
    const onJob = vi.fn();
    const poller = createTrainingJobPoller({ runId: 'run-01', read, onJob, onError: vi.fn(), intervalMs: 1000 });

    poller.start();
    await vi.advanceTimersByTimeAsync(0);
    expect(read).toHaveBeenCalledOnce();
    await vi.advanceTimersByTimeAsync(1000);
    expect(read).toHaveBeenCalledTimes(2);
    expect(onJob).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'completed' }));
    await vi.advanceTimersByTimeAsync(5000);
    expect(read).toHaveBeenCalledTimes(2);
  });

  it('cleans up pending timers and reports a safe polling error', async () => {
    vi.useFakeTimers();
    const onError = vi.fn();
    const read = vi.fn().mockRejectedValue(new Error('Job unavailable.'));
    const poller = createTrainingJobPoller({ runId: 'run-01', read, onJob: vi.fn(), onError, intervalMs: 1000 });

    poller.start();
    await vi.advanceTimersByTimeAsync(0);
    expect(onError).toHaveBeenCalledWith('Job unavailable.');
    poller.stop();
    await vi.advanceTimersByTimeAsync(5000);
    expect(read).toHaveBeenCalledOnce();
  });
});