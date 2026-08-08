import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  cancelInspectionRun,
  readLatestInspectionRun,
  readInspectionRun,
  startInspectionRun,
} from './inspection-service';


const RUN = {
  id: 'inspection-01', boardSerial: 'PCB-01', lot: '', recipeId: 1, resultId: null,
  status: 'queued', currentStep: 'queued', progressPercent: 0, cancelRequested: false,
  workflowSha256: 'a'.repeat(64), effectiveVersions: {}, parameters: {}, inputArtifact: null,
  decision: null, evidenceSha256: null, errorCode: null, errorMessage: null,
  createdAt: '2026-08-08T00:00:00Z', startedAt: null, completedAt: null, nodeRuns: [],
};

afterEach(() => vi.unstubAllGlobals());

describe('inspection runtime service', () => {
  it('creates, reads, and cancels persisted runs with authenticated requests', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(RUN), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(RUN), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(RUN), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ ...RUN, status: 'cancelled' }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await startInspectionRun('token', { boardSerial: 'PCB-01', lot: '', recipeId: 1, threshold: 0.5 });
    await readLatestInspectionRun('token');
    await readInspectionRun('token', RUN.id);
    const cancelled = await cancelInspectionRun('token', RUN.id);

    expect(cancelled.status).toBe('cancelled');
    expect(fetchMock.mock.calls.map((call) => new URL(call[0]).pathname)).toEqual([
      '/api/inspection-runs', '/api/inspection-runs/latest',
      '/api/inspection-runs/inspection-01', '/api/inspection-runs/inspection-01/cancel',
    ]);
    expect(fetchMock.mock.calls[0][1].method).toBe('POST');
    expect(fetchMock.mock.calls[3][1].method).toBe('POST');
  });
});