import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiRequest } from './api-client';


afterEach(() => {
  vi.unstubAllGlobals();
});


describe('API errors', () => {
  it('preserves structured validation details while deriving an operator message', async () => {
    const detail = [{ code: 'unknown-port', message: 'A connection port does not exist.', connectionId: 'edge-1' }];
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail }),
      { status: 422, headers: { 'Content-Type': 'application/json' } },
    )));

    await expect(apiRequest('/api/test')).rejects.toMatchObject({
      status: 422,
      message: 'A connection port does not exist.',
      detail,
    });
  });
});