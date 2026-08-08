import { afterEach, describe, expect, it, vi } from 'vitest';
import { activateSettings, createSettingsVersion, rollbackSettings, validateSettings } from './settings-service';

afterEach(() => vi.unstubAllGlobals());

describe('settings service', () => {
  it('preserves revision and idempotency contracts through the authenticated control plane', async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ revision: 2 }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    const identity = { scope: 'workstation' as const, subjectId: 'station-01', documentKey: 'workstation-profile' };

    await validateSettings('token', identity, { deploymentMode: 'simulation' });
    await createSettingsVersion('token', identity, 1, { deploymentMode: 'simulation' }, 'Validated change');
    await activateSettings('token', identity, 2, 'Apply profile', 'apply-2');
    await rollbackSettings('token', identity, 2, 1, 'Restore known profile');

    expect(fetchMock.mock.calls[0][0]).toContain('/api/v1/settings/workstation/station-01/validate');
    expect(JSON.parse(fetchMock.mock.calls[1][1]?.body as string).expectedRevision).toBe(1);
    expect(new Headers(fetchMock.mock.calls[2][1]?.headers).get('Idempotency-Key')).toBe('apply-2');
    expect(JSON.parse(fetchMock.mock.calls[3][1]?.body as string).targetRevision).toBe(1);
  });
});