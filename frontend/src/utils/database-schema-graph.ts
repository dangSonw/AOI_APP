import { Graph, layout } from '@dagrejs/dagre';
import { Position, type Edge, type Node } from '@xyflow/react';
import type { DatabaseSchema, DatabaseTable } from '../types/database-schema';

export type DatabaseTableNode = Node<{ table: DatabaseTable }, 'databaseTable'>;

export const DATABASE_TABLE_NODE_WIDTH = 340;

export function databaseTableNodeHeight(table: DatabaseTable): number {
  const metadataCount = table.indexes.length
    + table.constraints.unique.length
    + table.constraints.check.length;
  return 59 + table.columns.length * 43 + (metadataCount > 0 ? 14 + metadataCount * 16 : 0);
}

export function databaseTableId(schema: string, table: string): string {
  return `${schema}.${table}`;
}

export function mapDatabaseSchemaToGraph(schema: DatabaseSchema): {
  nodes: DatabaseTableNode[];
  edges: Edge[];
} {
  const edges = schema.tables.flatMap((table) => table.foreignKeys.map((foreignKey, index) => ({
    id: `${databaseTableId(table.schema, table.name)}:${foreignKey.name ?? index}`,
    source: databaseTableId(table.schema, table.name),
    target: databaseTableId(foreignKey.targetSchema, foreignKey.targetTable),
    label: `${foreignKey.sourceColumns.join(', ')} → ${foreignKey.targetColumns.join(', ')}`,
    type: 'smoothstep',
    animated: false,
  })));

  const graph = new Graph()
    .setGraph({ rankdir: 'LR', nodesep: 100, ranksep: 180, marginx: 40, marginy: 40 })
    .setDefaultEdgeLabel(() => ({}));
  schema.tables.forEach((table) => graph.setNode(databaseTableId(table.schema, table.name), {
    width: DATABASE_TABLE_NODE_WIDTH,
    height: databaseTableNodeHeight(table),
  }));
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  layout(graph);

  const nodes: DatabaseTableNode[] = schema.tables.map((table) => {
    const id = databaseTableId(table.schema, table.name);
    const position = graph.node(id);
    const height = databaseTableNodeHeight(table);
    return {
      id,
      type: 'databaseTable',
      position: {
        x: position.x - DATABASE_TABLE_NODE_WIDTH / 2,
        y: position.y - height / 2,
      },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      data: { table },
    };
  });

  return { nodes, edges };
}
