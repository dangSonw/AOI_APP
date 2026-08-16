import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
  type NodeTypes,
  useNodesState,
  useReactFlow,
} from '@xyflow/react';
import type { DatabaseSchema } from '../../types/database-schema';
import { mapDatabaseSchemaToGraph, type DatabaseTableNode as DatabaseTableNodeType } from '../../utils/database-schema-graph';
import { DatabaseTableNode } from './DatabaseTableNode';

const nodeTypes: NodeTypes = { databaseTable: DatabaseTableNode };

interface PostgreSQLSchemaPanelProps {
  schema: DatabaseSchema | null;
  isLoading: boolean;
  error: string;
  onRefresh?: () => void;
}

function SchemaGraphToolbar({
  isFullscreen,
  onReset,
  onToggleFullscreen,
}: {
  isFullscreen: boolean;
  onReset: () => void;
  onToggleFullscreen: () => Promise<void>;
}) {
  const { fitView } = useReactFlow();
  const fit = () => void fitView({ padding: 0.12, duration: 300 });
  const reset = () => {
    onReset();
    requestAnimationFrame(fit);
  };
  const toggleFullscreen = async () => {
    await onToggleFullscreen();
    requestAnimationFrame(fit);
  };

  return (
    <Panel className="database-schema-graph__toolbar" position="top-right">
      <span>Drag tables to adjust</span>
      <button type="button" onClick={reset}>Reset layout</button>
      <button type="button" onClick={fit}>Fit graph</button>
      <button type="button" onClick={() => void toggleFullscreen()}>{isFullscreen ? 'Exit full screen' : 'Full screen'}</button>
    </Panel>
  );
}

export function PostgreSQLSchemaPanel({ schema, isLoading, error, onRefresh }: PostgreSQLSchemaPanelProps) {
  const graph = useMemo(() => schema ? mapDatabaseSchemaToGraph(schema) : { nodes: [], edges: [] }, [schema]);
  const [nodes, setNodes, onNodesChange] = useNodesState<DatabaseTableNodeType>(graph.nodes);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => setNodes(graph.nodes), [graph.nodes, setNodes]);
  useEffect(() => {
    const updateFullscreenState = () => setIsFullscreen(document.fullscreenElement === panelRef.current);
    document.addEventListener('fullscreenchange', updateFullscreenState);
    return () => document.removeEventListener('fullscreenchange', updateFullscreenState);
  }, []);

  const toggleFullscreen = async () => {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await panelRef.current?.requestFullscreen();
  };

  if (isLoading) return <div className="database-schema-state" role="status">Loading PostgreSQL schema…</div>;
  if (error) return <div className="database-schema-state database-schema-state--error" role="alert"><span>{error}</span>{onRefresh && <button className="studio-secondary-button" type="button" onClick={onRefresh}>Retry</button>}</div>;
  if (!schema || schema.tables.length === 0) return <div className="database-schema-state">No tables found in schema.</div>;

  return (
    <section ref={panelRef} className="database-schema-panel" aria-label="PostgreSQL database schema">
      <header className="section-heading">
        <div><span className="overline">{schema.databaseDialect} · {schema.defaultSchema}</span><h2>Schema graph</h2></div>
        <div className="database-schema-panel__summary"><span>{schema.tables.length} tables · {graph.edges.length} foreign keys</span>{onRefresh && <button className="studio-secondary-button" type="button" onClick={onRefresh}>Refresh schema</button>}</div>
      </header>
      <div className="database-schema-graph">
        <ReactFlow
          nodes={nodes}
          edges={graph.edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          nodesDraggable
          nodesConnectable={false}
          elementsSelectable
          deleteKeyCode={null}
          fitView
          fitViewOptions={{ padding: 0.12 }}
          minZoom={0.12}
          maxZoom={1.8}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={18} size={1} color="#b9cadb" />
          <Controls position="bottom-left" showInteractive={false} />
          <MiniMap position="bottom-right" pannable zoomable nodeColor="#336791" maskColor="rgba(238,243,248,.82)" />
          <SchemaGraphToolbar
            isFullscreen={isFullscreen}
            onReset={() => setNodes(graph.nodes)}
            onToggleFullscreen={toggleFullscreen}
          />
        </ReactFlow>
      </div>
    </section>
  );
}