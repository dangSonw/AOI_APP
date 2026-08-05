import { useCallback, useMemo, useState } from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Connection,
  type Edge,
  type EdgeChange,
  type IsValidConnection,
  type NodeChange,
  type NodeTypes,
} from '@xyflow/react';
import type { AlgorithmDefinition, ConnectionDraft, Workflow } from '../../types/workflow';
import { validateConnection } from '../../utils/workflow-graph';
import { ALGORITHM_DRAG_TYPE } from './AlgorithmCatalog';
import { WorkflowNode, type WorkflowFlowNode } from './WorkflowNode';


interface WorkflowCanvasProps {
  workflow: Workflow;
  catalog: AlgorithmDefinition[];
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string | null) => void;
  onAddAlgorithm: (definition: AlgorithmDefinition, position: { x: number; y: number }) => void;
  onMoveNode: (nodeId: string, position: { x: number; y: number }) => void;
  onConnect: (connection: ConnectionDraft) => void;
  onRemoveNode: (nodeId: string) => void;
  onRemoveConnection: (connectionId: string) => void;
  onConnectionRejected: (message: string) => void;
}

const nodeTypes: NodeTypes = { workflow: WorkflowNode };

function CanvasContent(props: WorkflowCanvasProps) {
  const { screenToFlowPosition } = useReactFlow<WorkflowFlowNode, Edge>();
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const nodes = useMemo<WorkflowFlowNode[]>(() => props.workflow.nodes.map((node) => ({
    id: node.id,
    type: 'workflow',
    position: node.position,
    selected: node.id === props.selectedNodeId,
    data: { value: node, onRemove: props.onRemoveNode },
  })), [props.workflow.nodes, props.selectedNodeId, props.onRemoveNode]);
  const edges = useMemo<Edge[]>(() => props.workflow.connections.map((connection) => ({
    id: connection.id,
    source: connection.sourceNodeId,
    sourceHandle: connection.sourcePortId,
    target: connection.targetNodeId,
    targetHandle: connection.targetPortId,
    type: 'smoothstep',
    selected: connection.id === selectedEdgeId,
  })), [props.workflow.connections, selectedEdgeId]);

  const toDraft = useCallback((connection: Connection | Edge): ConnectionDraft | null => {
    if (!connection.source || !connection.target || !connection.sourceHandle || !connection.targetHandle) return null;
    return {
      sourceNodeId: connection.source,
      sourcePortId: connection.sourceHandle,
      targetNodeId: connection.target,
      targetPortId: connection.targetHandle,
    };
  }, []);
  const isValidConnection: IsValidConnection<Edge> = useCallback((candidate) => {
    const draft = toDraft(candidate);
    return draft !== null && validateConnection(props.workflow, draft) === null;
  }, [props.workflow, toDraft]);

  const handleConnect = useCallback((candidate: Connection) => {
    const draft = toDraft(candidate);
    if (!draft) return;
    const connectionIssue = validateConnection(props.workflow, draft);
    if (connectionIssue) {
      props.onConnectionRejected(connectionIssue.message);
      return;
    }
    props.onConnect(draft);
  }, [props, toDraft]);

  const handleNodesChange = useCallback((changes: NodeChange<WorkflowFlowNode>[]) => {
    for (const change of changes) {
      if (change.type === 'position' && change.position) props.onMoveNode(change.id, change.position);
      if (change.type === 'remove') props.onRemoveNode(change.id);
      if (change.type === 'select' && change.selected) props.onSelectNode(change.id);
    }
  }, [props]);

  const handleEdgesChange = useCallback((changes: EdgeChange<Edge>[]) => {
    for (const change of changes) {
      if (change.type === 'select') setSelectedEdgeId(change.selected ? change.id : null);
      if (change.type === 'remove') {
        props.onRemoveConnection(change.id);
        setSelectedEdgeId((current) => current === change.id ? null : current);
      }
    }
  }, [props]);

  return (
    <div
      className="workflow-canvas"
      onDragOver={(event) => {
        if (event.dataTransfer.types.includes(ALGORITHM_DRAG_TYPE)) {
          event.preventDefault();
          event.dataTransfer.dropEffect = 'copy';
        }
      }}
      onDrop={(event) => {
        event.preventDefault();
        const definition = props.catalog.find((item) => item.id === event.dataTransfer.getData(ALGORITHM_DRAG_TYPE));
        if (definition) props.onAddAlgorithm(definition, screenToFlowPosition({ x: event.clientX, y: event.clientY }));
      }}
      onKeyDown={(event) => {
        if (selectedEdgeId && (event.key === 'Delete' || event.key === 'Backspace')) {
          event.preventDefault();
          props.onRemoveConnection(selectedEdgeId);
          setSelectedEdgeId(null);
        }
      }}
    >
      <ReactFlow<WorkflowFlowNode, Edge>
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={handleConnect}
        isValidConnection={isValidConnection}
        onNodeClick={(_, node) => props.onSelectNode(node.id)}
        onPaneClick={() => { props.onSelectNode(null); setSelectedEdgeId(null); }}
        onEdgeClick={(_, edge) => setSelectedEdgeId(edge.id)}
        onEdgesDelete={(deleted) => deleted.forEach((edge) => props.onRemoveConnection(edge.id))}
        onEdgeDoubleClick={(_, edge) => props.onRemoveConnection(edge.id)}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.25}
        maxZoom={2}
        deleteKeyCode={['Backspace', 'Delete']}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={18} size={1} color="#b9cadb" />
        <Controls position="bottom-left" showInteractive={false} />
        <MiniMap position="bottom-right" pannable zoomable nodeColor="#1769e0" maskColor="rgba(238,243,248,.82)" />
      </ReactFlow>
      {nodes.length === 0 && (
        <div className="workflow-canvas__empty">
          <span aria-hidden="true">＋</span><strong>Start with Image input</strong><p>Drag a catalog method here or use its Add button.</p>
        </div>
      )}
    </div>
  );
}

export function WorkflowCanvas(props: WorkflowCanvasProps) {
  return <ReactFlowProvider><CanvasContent {...props} /></ReactFlowProvider>;
}