import { afterEach, describe, expect, it, vi } from 'vitest';
import { readVisualizationArtifact } from './visualization-service';

describe('visualization artifact service', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('loads and validates structured artifacts with authenticated no-store requests', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ schema: 'aoi.table.v1', columns: [{ key: 'x', label: 'X', type: 'number' }], rows: [{ x: 1 }] }),
      { status: 200, headers: { 'Content-Type': 'application/json', 'Content-Length': '109' } },
    ));
    vi.stubGlobal('fetch', fetchMock);

    const result = await readVisualizationArtifact('token-1', '/api/v1/research/artifacts/8');

    expect(result.kind).toBe('structured');
    const [, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(new Headers(request.headers).get('Authorization')).toBe('Bearer token-1');
    expect(request.cache).toBe('no-store');
  });

  it('rejects malformed and oversized structured artifacts', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(new Response('{bad', {
      status: 200, headers: { 'Content-Type': 'application/json' },
    })).mockResolvedValueOnce(new Response('x'.repeat(2 * 1024 * 1024 + 1), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    })));

    await expect(readVisualizationArtifact('token', '/api/v1/research/artifacts/1')).rejects.toThrow('malformed');
    await expect(readVisualizationArtifact('token', '/api/v1/research/artifacts/2')).rejects.toThrow('2 MB');
  });

  it('returns supported image media as a static fallback', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new Blob(['png']), {
      status: 200, headers: { 'Content-Type': 'image/png', 'Content-Length': '3' },
    })));

    const result = await readVisualizationArtifact('token', '/api/v1/research/artifacts/3');

    expect(result).toMatchObject({ kind: 'media', mediaType: 'image/png' });
  });
});