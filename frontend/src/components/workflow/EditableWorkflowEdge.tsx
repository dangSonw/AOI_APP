import { useEffect, useMemo, useState, type PointerEvent as ReactPointerEvent } from 'react';
import { BaseEdge, useReactFlow, type Edge, type EdgeProps } from '@xyflow/react';
import type { WorkflowPoint } from '../../types/workflow';


export interface EditableEdgeData extends Record<string, unknown> {
  waypoints: WorkflowPoint[];
  onWaypointsChange: (edgeId: string, waypoints: WorkflowPoint[]) => void;
}

export type EditableEdge = Edge<EditableEdgeData, 'editable'>;

export function defaultOrthogonalWaypoints(source: WorkflowPoint, target: WorkflowPoint): WorkflowPoint[] {
  const middleX = (source.x + target.x) / 2;
  return [{ x: middleX, y: source.y }, { x: middleX, y: target.y }];
}

export function orthogonalPath(points: WorkflowPoint[]): string {
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');
}

export function moveOrthogonalSegment(
  points: WorkflowPoint[],
  segmentIndex: number,
  position: WorkflowPoint,
): WorkflowPoint[] {
  const start = points[segmentIndex];
  const end = points[segmentIndex + 1];
  if (!start || !end) return points;
  const horizontal = Math.abs(end.x - start.x) >= Math.abs(end.y - start.y);
  const next = points.map((point) => ({ ...point }));

  if (segmentIndex === 0) next.splice(1, 0, { ...start });
  const adjustedIndex = segmentIndex === 0 ? 1 : segmentIndex;
  if (segmentIndex === points.length - 2) next.splice(next.length - 1, 0, { ...end });

  if (horizontal) {
    next[adjustedIndex].y = position.y;
    next[adjustedIndex + 1].y = position.y;
  } else {
    next[adjustedIndex].x = position.x;
    next[adjustedIndex + 1].x = position.x;
  }
  return next;
}

export function EditableWorkflowEdge({
  id, sourceX, sourceY, targetX, targetY, selected, data, markerStart, markerEnd, style,
}: EdgeProps<EditableEdge>) {
  const { screenToFlowPosition } = useReactFlow();
  const source = useMemo(() => ({ x: sourceX, y: sourceY }), [sourceX, sourceY]);
  const target = useMemo(() => ({ x: targetX, y: targetY }), [targetX, targetY]);
  const storedWaypoints = data?.waypoints ?? [];
  const [draggedPoints, setDraggedPoints] = useState<WorkflowPoint[] | null>(null);
  const points = draggedPoints ?? [
    source,
    ...(storedWaypoints.length > 0 ? storedWaypoints : defaultOrthogonalWaypoints(source, target)),
    target,
  ];

  useEffect(() => setDraggedPoints(null), [sourceX, sourceY, targetX, targetY, storedWaypoints]);

  const startSegmentDrag = (event: ReactPointerEvent<SVGCircleElement>, segmentIndex: number) => {
    event.preventDefault();
    event.stopPropagation();
    const initialPoints = points;
    const handleMove = (moveEvent: PointerEvent) => {
      setDraggedPoints(moveOrthogonalSegment(
        initialPoints,
        segmentIndex,
        screenToFlowPosition({ x: moveEvent.clientX, y: moveEvent.clientY }),
      ));
    };
    const handleUp = (upEvent: PointerEvent) => {
      const finalPoints = moveOrthogonalSegment(
        initialPoints,
        segmentIndex,
        screenToFlowPosition({ x: upEvent.clientX, y: upEvent.clientY }),
      );
      setDraggedPoints(null);
      data?.onWaypointsChange(id, finalPoints.slice(1, -1));
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };
    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
  };

  return (
    <>
      <BaseEdge path={orthogonalPath(points)} markerStart={markerStart} markerEnd={markerEnd} style={style} />
      {selected && points.slice(0, -1).map((point, index) => {
        const next = points[index + 1];
        const horizontal = Math.abs(next.x - point.x) >= Math.abs(next.y - point.y);
        return (
          <circle
            key={`${index}-${point.x}-${point.y}`}
            className={`workflow-edge-handle workflow-edge-handle--${horizontal ? 'horizontal' : 'vertical'} nodrag nopan`}
            cx={(point.x + next.x) / 2}
            cy={(point.y + next.y) / 2}
            r={6}
            onPointerDown={(event) => startSegmentDrag(event, index)}
          >
            <title>Drag to move {horizontal ? 'horizontal' : 'vertical'} wire segment</title>
          </circle>
        );
      })}
    </>
  );
}