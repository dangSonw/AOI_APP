import { describe, expect, it } from 'vitest';
import { defaultOrthogonalWaypoints, moveOrthogonalSegment, orthogonalPath } from './EditableWorkflowEdge';


describe('editable orthogonal workflow edge', () => {
  it('moves horizontal segments vertically and vertical segments horizontally', () => {
    const points = [{ x: 0, y: 0 }, ...defaultOrthogonalWaypoints({ x: 0, y: 0 }, { x: 100, y: 80 }), { x: 100, y: 80 }];

    const horizontal = moveOrthogonalSegment(points, 0, { x: 20, y: 25 });
    expect(horizontal.slice(0, 3)).toEqual([{ x: 0, y: 0 }, { x: 0, y: 25 }, { x: 50, y: 25 }]);

    const vertical = moveOrthogonalSegment(points, 1, { x: 70, y: 40 });
    expect(vertical[1].x).toBe(70);
    expect(vertical[2].x).toBe(70);
    expect(orthogonalPath(vertical)).toContain('L 70 80');
  });
});