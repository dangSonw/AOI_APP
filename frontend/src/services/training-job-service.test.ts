import { afterEach, describe, expect, it, vi } from 'vitest';
import { cancelTrainingJob, createTrainingJob, readTrainingJob } from './training-job-service';
import type { TrainingJobCreate } from '../types/training-job';

afterEach(() => vi.unstubAllGlobals());

const request: TrainingJobCreate = {
  experimentId: 'experiment-01',
  recipeSlug: 'recipe-01',
  workflowRevision: 4,
  nodeInstanceId: 'node-01',
  nodeId: 'fake-trainer',
  nodePackageVersion: '1.2.0',
  actionName: 'train',
  executionTarget: 'local-cpu',
  datasetBindings: {
    training: { datasetId: 'cats-dogs', version: `sha256:${'a'.repeat(64)}` },
  },
  parameters: { epochs: 2 },
  randomSeeds: { python: 42 },
  parentRunId: null,
};

describe('training job service', () => {
  it('creates an authenticated training job with the exact client-authored payload', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: 'run-01' }), { status: 201 }));
    vi.stubGlobal('fetch', fetchMock);

    await createTrainingJob('token', request);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/research/training-jobs'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(request),
        headers: expect.any(Headers),
      }),
    );
    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer token');
  });

  it('reads and cancels an encoded run through the authenticated API', async () => {
    const fetchMock = vi.fn().mockImplementation(
      () => Promise.resolve(new Response(JSON.stringify({ id: 'run/01' }), { status: 200 })),
    );
    vi.stubGlobal('fetch', fetchMock);

    await readTrainingJob('token', 'run/01');
    await cancelTrainingJob('token', 'run/01');

    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/research/training-jobs/run%2F01');
    expect(fetchMock.mock.calls[1][0]).toContain('/api/v1/research/training-jobs/run%2F01/cancellations');
    expect(fetchMock.mock.calls[1][1]).toEqual(expect.objectContaining({ method: 'POST' }));
  });
});