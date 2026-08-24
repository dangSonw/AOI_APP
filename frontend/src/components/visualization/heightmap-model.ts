import type { HeightmapPayload } from '../../types/visualization';

export interface HeightmapView { yaw: number; pitch: number; zoom: number }

export function summarizeHeightmap(payload: HeightmapPayload) {
  let minimum = Infinity, maximum = -Infinity, validCount = 0;
  for (const row of payload.values) for (const value of row) {
    if (value !== null) { minimum = Math.min(minimum, value); maximum = Math.max(maximum, value); validCount += 1; }
  }
  return { rows: payload.rows, columns: payload.columns, validCount, missingCount: payload.rows * payload.columns - validCount, minimum, maximum, unit: payload.unit };
}

export function createHeightmapModel(payload: HeightmapPayload) {
  const positions = new Float32Array(payload.rows * payload.columns * 3);
  const valid: boolean[] = [];
  for (let row = 0; row < payload.rows; row += 1) {
    for (let column = 0; column < payload.columns; column += 1) {
      const index = row * payload.columns + column, value = payload.values[row][column];
      positions[index * 3] = (column - (payload.columns - 1) / 2) * payload.xSpacing;
      positions[index * 3 + 1] = (row - (payload.rows - 1) / 2) * payload.ySpacing;
      positions[index * 3 + 2] = value ?? 0;
      valid[index] = value !== null;
    }
  }
  const indices: number[] = [];
  for (let row = 0; row < payload.rows - 1; row += 1) {
    for (let column = 0; column < payload.columns - 1; column += 1) {
      const a = row * payload.columns + column, b = a + 1, c = a + payload.columns, d = c + 1;
      if (valid[a] && valid[c] && valid[b]) indices.push(a, c, b);
      if (valid[b] && valid[c] && valid[d]) indices.push(b, c, d);
    }
  }
  return {
    positions, indices: new Uint32Array(indices),
    summary: summarizeHeightmap(payload),
  };
}

export function updateHeightmapView(view: HeightmapView, key: string): HeightmapView {
  if (key === '0' || key === 'Home') return { yaw: 45, pitch: 35, zoom: 1 };
  if (key === 'ArrowLeft' || key === 'ArrowRight') return { ...view, yaw: view.yaw + (key === 'ArrowLeft' ? -5 : 5) };
  if (key === 'ArrowUp' || key === 'ArrowDown') return { ...view, pitch: Math.max(5, Math.min(85, view.pitch + (key === 'ArrowUp' ? 5 : -5))) };
  if (key === '+' || key === '=') return { ...view, zoom: Math.min(3, view.zoom + 0.1) };
  if (key === '-') return { ...view, zoom: Math.max(0.5, view.zoom - 0.1) };
  return view;
}