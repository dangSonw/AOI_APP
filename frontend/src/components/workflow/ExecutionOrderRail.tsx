import { useState } from 'react';
import type { ValidationIssue, Workflow } from '../../types/workflow';
import { moveExecutionNode } from '../../utils/workflow-graph';


interface ExecutionOrderRailProps {
  workflow: Workflow;
  issues: ValidationIssue[];
  onChange: (order: string[]) => void;
  onAutoOrder: () => void;
  onSelectNode: (nodeId: string) => void;
}

export function ExecutionOrderRail({ workflow, issues, onChange, onAutoOrder, onSelectNode }: ExecutionOrderRailProps) {
  const [draggedNodeId, setDraggedNodeId] = useState<string | null>(null);
  const nodes = new Map(workflow.nodes.map((node) => [node.id, node]));
  const orderIssues = issues.filter((issue) => issue.code === 'dependency-order' || issue.code === 'execution-order-mismatch' || issue.code === 'cycle');

  const moveTo = (nodeId: string, targetId: string) => {
    const next = workflow.executionOrder.filter((id) => id !== nodeId);
    const targetIndex = next.indexOf(targetId);
    next.splice(targetIndex < 0 ? next.length : targetIndex, 0, nodeId);
    onChange(next);
  };

  return (
    <section className="execution-rail" aria-label="Execution order">
      <header className="workflow-region-heading">
        <div><span className="overline">Deterministic sequence</span><strong>Execution order</strong></div>
        <button type="button" className="secondary-button" onClick={onAutoOrder}>Auto order</button>
      </header>
      {orderIssues.length > 0 && <p className="execution-rail__warning" role="status">{orderIssues[0].message}</p>}
      <ol className="execution-rail__list">
        {workflow.executionOrder.map((nodeId, index) => {
          const node = nodes.get(nodeId);
          if (!node) return null;
          return (
            <li
              draggable
              key={nodeId}
              onDragStart={() => setDraggedNodeId(nodeId)}
              onDragOver={(event) => event.preventDefault()}
              onDrop={() => {
                if (draggedNodeId && draggedNodeId !== nodeId) moveTo(draggedNodeId, nodeId);
                setDraggedNodeId(null);
              }}
            >
              <button type="button" className="execution-rail__node" onClick={() => onSelectNode(nodeId)}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <span><strong>{node.displayName}</strong><small>{node.algorithmId}</small></span>
                <em>Configuration only</em>
              </button>
              <div className="execution-rail__moves">
                <button type="button" disabled={index === 0} aria-label={`Move ${node.displayName} up`} onClick={() => onChange(moveExecutionNode(workflow.executionOrder, nodeId, -1))}>↑</button>
                <button type="button" disabled={index === workflow.executionOrder.length - 1} aria-label={`Move ${node.displayName} down`} onClick={() => onChange(moveExecutionNode(workflow.executionOrder, nodeId, 1))}>↓</button>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}