import { afterEach, describe, expect, it, vi } from 'vitest';
import { createRegisteredModel, createRegisteredModelVersion, promoteModel, readModelEvents, readModelRollbackPreview, readResearchRunArtifacts, resolveProductionBindings, rollbackModel, searchResearchRuns } from './research-service';

afterEach(() => vi.unstubAllGlobals());

describe('research model lifecycle service', () => {
  it('encodes the complete research search query', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('[]', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await searchResearchRuns('token', 'revision / local-cpu');

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/research/runs?query=revision%20%2F%20local-cpu'),
      expect.any(Object),
    );
  });

  it('creates a model and registers a validated run artifact', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ name: 'pcb-classifier' }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ modelName: 'pcb-classifier', version: 1 }), { status: 201 }));
    vi.stubGlobal('fetch', fetchMock);

    await createRegisteredModel('token', { name: 'pcb-classifier', description: 'Board classifier' });
    await createRegisteredModelVersion('token', 'pcb-classifier', {
      runId: 'run-01', artifactId: 17, validationEvidence: { passed: true },
    });

    expect(fetchMock).toHaveBeenNthCalledWith(1,
      expect.stringContaining('/api/v1/models'),
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ name: 'pcb-classifier', description: 'Board classifier' }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2,
      expect.stringContaining('/api/v1/models/pcb-classifier/versions'),
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ runId: 'run-01', artifactId: 17, validationEvidence: { passed: true } }) }),
    );
  });

  it('reads safe artifact metadata for a selected source run', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('[]', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await readResearchRunArtifacts('token', 'run/01');

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/research/runs/run%2F01/artifacts'),
      expect.any(Object),
    );
  });

  it('sends a version and reason when promoting an alias', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ action: 'promote', alias: 'champion', nextVersion: 3, reason: 'Validated on golden fixture' }), { status: 201 }));
    vi.stubGlobal('fetch', fetchMock);

    await promoteModel('token', 'pcb/classifier', 'champion', 3, 'Validated on golden fixture');

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/models/pcb%2Fclassifier/aliases/champion/promotions'),
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ version: 3, reason: 'Validated on golden fixture' }) }),
    );
  });

  it('resolves a portable model reference through the production binding endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ model: { modelName: 'pcb-classifier', modelVersion: 4, artifactSha256: 'a'.repeat(64) } }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const payload = { model: { modelName: 'pcb-classifier', alias: 'champion' } };

    await resolveProductionBindings('token', payload);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/models/resolve-production-bindings'),
      expect.objectContaining({ method: 'POST', body: JSON.stringify(payload) }),
    );
  });

  it('sends a reason when rolling back an alias', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ action: 'rollback', alias: 'champion', nextVersion: 2, reason: 'Restore validated release' }), { status: 201 }));
    vi.stubGlobal('fetch', fetchMock);

    await rollbackModel('token', 'pcb-classifier', 'champion', 'Restore validated release', 17);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/models/pcb-classifier/aliases/champion/rollback'),
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ reason: 'Restore validated release', previewEventId: 17 }) }),
    );
  });

  it('reads the rollback target before confirmation', async () => {
    const preview = { alias: 'champion', currentVersion: 3, targetVersion: 2, previewEventId: 17 };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(preview), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(readModelRollbackPreview('token', 'pcb/classifier', 'champion')).resolves.toEqual(preview);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/models/pcb%2Fclassifier/aliases/champion/rollback-preview'),
      expect.any(Object),
    );
  });

  it('reads append-only model lifecycle events', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('[]', { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await readModelEvents('token', 'pcb/classifier');

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/models/pcb%2Fclassifier/events'),
      expect.any(Object),
    );
  });
});
