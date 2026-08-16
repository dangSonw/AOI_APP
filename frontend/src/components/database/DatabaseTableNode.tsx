import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { DatabaseTableNode } from '../../utils/database-schema-graph';

function columnFlags(primaryKey: boolean, nullable: boolean): string {
  return [primaryKey ? 'PK' : '', nullable ? 'NULL' : 'NOT NULL'].filter(Boolean).join(' · ');
}

export function DatabaseTableNode({ data }: NodeProps<DatabaseTableNode>) {
  const { table } = data;
  const unique = table.constraints.unique;
  const checks = table.constraints.check;

  return (
    <article className="database-table-node" aria-label={`${table.schema}.${table.name} database table`}>
      <Handle type="target" position={Position.Left} isConnectable={false} />
      <header><span>{table.schema}</span><strong>{table.name}</strong></header>
      <div className="database-table-node__columns">
        {table.columns.map((column) => (
          <div key={column.name}>
            <span><strong>{column.name}</strong><small>{columnFlags(column.primaryKey, column.nullable)}</small></span>
            <code>{column.dataType}</code>
          </div>
        ))}
      </div>
      {(table.indexes.length > 0 || unique.length > 0 || checks.length > 0) && (
        <div className="database-table-node__metadata">
          {table.indexes.map((index, position) => (
            <span key={`index-${index.name ?? position}`}><b>IDX</b> {index.name ?? index.columnNames.join(', ')}{index.unique ? ' · unique' : ''}</span>
          ))}
          {unique.map((constraint, position) => (
            <span key={`unique-${constraint.name ?? position}`}><b>UQ</b> {constraint.name ?? constraint.columnNames.join(', ')}</span>
          ))}
          {checks.map((constraint, position) => (
            <span key={`check-${constraint.name ?? position}`} title={constraint.expression}><b>CHK</b> {constraint.name ?? constraint.expression}</span>
          ))}
        </div>
      )}
      <Handle type="source" position={Position.Right} isConnectable={false} />
    </article>
  );
}