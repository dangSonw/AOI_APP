import { describe, expect, it } from 'vitest';
import { createHeightmapModel, updateHeightmapView } from './heightmap-model';

const payload = {
  schema: 'aoi.heightmap.v1' as const, rows: 2, columns: 3,
  values: [[0, 1, null], [2, 3, 4]], xSpacing: 0.5, ySpacing: 1, unit: 'μm',
};

describe('heightmap renderer model', () => {
  it('creates bounded geometry and semantic statistics without filling missing samples', () => {
    const model = createHeightmapModel(payload);
    expect(model.positions).toHaveLength(18);
    expect(Array.from(model.indices)).toEqual([0, 3, 1, 1, 3, 4]);
    expect(model.summary).toEqual({ rows: 2, columns: 3, validCount: 5, missingCount: 1, minimum: 0, maximum: 4, unit: 'μm' });
  });

  it('maps keyboard controls to bounded orbit, zoom, and reset state', () => {
    const initial = { yaw: 45, pitch: 35, zoom: 1 };
    expect(updateHeightmapView(initial, 'ArrowLeft')).toEqual({ ...initial, yaw: 40 });
    expect(updateHeightmapView(initial, 'ArrowUp')).toEqual({ ...initial, pitch: 40 });
    expect(updateHeightmapView(initial, '+')).toEqual({ ...initial, zoom: 1.1 });
    expect(updateHeightmapView({ yaw: 10, pitch: 80, zoom: 4 }, '0')).toEqual(initial);
  });

  it('builds the fixed H-S/H-M/H-L fixtures within the bounded buffer budget', () => {
    for (const size of [128, 256, 512]) {
      const benchmark = {
        schema: 'aoi.heightmap.v1' as const, rows: size, columns: size,
        values: Array.from({ length: size }, (_, row) => Array.from({ length: size }, (_, column) => row + column)),
        xSpacing: 1, ySpacing: 1, unit: 'μm',
      };
      const model = createHeightmapModel(benchmark);
      expect(model.positions.byteLength + model.indices.byteLength).toBeLessThan(10 * 1024 * 1024);
      expect(model.indices).toHaveLength((size - 1) * (size - 1) * 6);
    }
  }, 10_000);
});