import { afterEach, describe, expect, it, vi } from 'vitest';
import { readDatabaseSchema } from './database-schema-service';

afterEach(() => vi.unstubAllGlobals());

describe('database schema service', () => {
  it('reads authenticated schema metadata', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      databaseDialect: 'postgresql', defaultSchema: 'public', tables: [],
    }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await readDatabaseSchema('token');

    expect(new URL(fetchMock.mock.calls[0][0]).pathname).toBe('/api/database/schema');
    expect(new Headers(fetchMock.mock.calls[0][1].headers).get('Authorization')).toBe('Bearer token');
  });
});