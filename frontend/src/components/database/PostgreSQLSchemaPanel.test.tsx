import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { PostgreSQLSchemaPanel } from './PostgreSQLSchemaPanel';

describe('PostgreSQLSchemaPanel states', () => {
  it('renders loading, error, and empty states', () => {
    expect(renderToStaticMarkup(<PostgreSQLSchemaPanel isLoading error="" schema={null} />)).toContain('Loading PostgreSQL schema');
    expect(renderToStaticMarkup(<PostgreSQLSchemaPanel isLoading={false} error="Schema unavailable" schema={null} />)).toContain('Schema unavailable');
    expect(renderToStaticMarkup(<PostgreSQLSchemaPanel isLoading={false} error="" schema={{ databaseDialect: 'postgresql', defaultSchema: 'public', tables: [] }} />)).toContain('No tables found');
  });

  it('offers movable tables, layout reset, fit view, and fullscreen viewing', () => {
    const markup = renderToStaticMarkup(<PostgreSQLSchemaPanel
      isLoading={false}
      error=""
      schema={{
        databaseDialect: 'postgresql',
        defaultSchema: 'public',
        tables: [{
          schema: 'public', name: 'users', columns: [], indexes: [], foreignKeys: [],
          constraints: { primaryKey: null, unique: [], check: [] },
        }],
      }}
    />);

    expect(markup).toContain('Drag tables to adjust');
    expect(markup).toContain('Reset layout');
    expect(markup).toContain('Fit graph');
    expect(markup).toContain('Full screen');
  });
});