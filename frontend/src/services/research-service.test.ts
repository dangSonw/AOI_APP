import { afterEach, describe, expect, it, vi } from 'vitest';
import { promoteModel, resolveProductionBindings, rollbackModel } from './research-service';

afterEach(() => vi.unstubAllGlobals());

describe('research model lifecycle service', () => {
  it('sends a version and reason when promoting an alias', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ action: 'promote', alias: 'champion', nextVersion: 3, reason: 'Validated on golden fixture' }), { status: 201 }));
    vi.stubGlobal('fetch', fetchMock);

    await promoteModel('token', 'pcb/classifier', 'champion', 3, 'Validated on golden fixture');

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/models/pcb%2Fclassifier/aliases/champion/promotions'),
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

    await rollbackModel('token', 'pcb-classifier', 'champion', 'Restore validated release');

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/models/pcb-classifier/aliases/champion/rollback'),
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ reason: 'Restore validated release' }) }),
    );
  });
});
