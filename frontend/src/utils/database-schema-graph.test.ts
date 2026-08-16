import { describe, expect, it } from 'vitest';
import type { DatabaseSchema } from '../types/database-schema';
import {
  DATABASE_TABLE_NODE_WIDTH,
  databaseTableNodeHeight,
  mapDatabaseSchemaToGraph,
} from './database-schema-graph';

const schema: DatabaseSchema = {
  databaseDialect: 'postgresql',
  defaultSchema: 'public',
  tables: [
    {
      schema: 'public', name: 'users', columns: [], indexes: [],
      constraints: { primaryKey: null, unique: [], check: [] }, foreignKeys: [],
    },
    {
      schema: 'public', name: 'inspections', columns: [], indexes: [],
      constraints: { primaryKey: null, unique: [], check: [] },
      foreignKeys: [{
        name: 'fk_inspections_user', sourceColumns: ['user_id'], targetSchema: 'public',
        targetTable: 'users', targetColumns: ['id'], onUpdate: null, onDelete: null,
      }],
    },
  ],
};

describe('database schema graph mapping', () => {
  it('maps tables to nodes and foreign keys to read-only edges', () => {
    const graph = mapDatabaseSchemaToGraph(schema);

    expect(graph.nodes.map((node) => node.id)).toEqual(['public.users', 'public.inspections']);
    expect(graph.edges).toEqual([expect.objectContaining({
      source: 'public.inspections',
      target: 'public.users',
      label: 'user_id → id',
    })]);
  });

  it('lays out foreign keys left-to-right without overlapping tall tables', () => {
    const tallColumns = Array.from({ length: 20 }, (_, index) => ({
      name: `column_${index}`,
      dataType: 'varchar(255)',
      nullable: false,
      default: null,
      primaryKey: false,
    }));
    const graph = mapDatabaseSchemaToGraph({
      ...schema,
      tables: [
        { ...schema.tables[0], columns: tallColumns },
        schema.tables[1],
        { ...schema.tables[0], name: 'audit_log', columns: tallColumns },
      ],
    });
    const users = graph.nodes.find((node) => node.id === 'public.users')!;
    const inspections = graph.nodes.find((node) => node.id === 'public.inspections')!;
    const auditLog = graph.nodes.find((node) => node.id === 'public.audit_log')!;

    expect(inspections.position.x + DATABASE_TABLE_NODE_WIDTH).toBeLessThan(users.position.x);
    for (const [left, right] of [[users, inspections], [users, auditLog], [inspections, auditLog]]) {
      const separatedHorizontally = left.position.x + DATABASE_TABLE_NODE_WIDTH <= right.position.x
        || right.position.x + DATABASE_TABLE_NODE_WIDTH <= left.position.x;
      const separatedVertically = left.position.y + databaseTableNodeHeight(left.data.table) <= right.position.y
        || right.position.y + databaseTableNodeHeight(right.data.table) <= left.position.y;
      expect(separatedHorizontally || separatedVertically).toBe(true);
    }
  });
});