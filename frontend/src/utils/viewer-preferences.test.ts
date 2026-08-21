import { describe, expect, it } from 'vitest';
import { createDefaultPreferences, getViewerPreference, updateViewerPreference } from './workstation-preferences';

describe('viewer preference helpers', () => {
  it('stores independent dimensions for each workflow output', () => {
    const preferences = createDefaultPreferences(1, 'station-01');
    const updated = updateViewerPreference(preferences, 'image-2', { widthUnits: 9, heightUnits: 8 });

    expect(getViewerPreference(updated, 'image-1')).toEqual({ isCollapsed: false, widthUnits: 6, heightUnits: 5 });
    expect(getViewerPreference(updated, 'image-2')).toEqual({ isCollapsed: false, widthUnits: 9, heightUnits: 8 });
  });

  it('clamps dimensions while preserving collapse state', () => {
    const preferences = createDefaultPreferences(1, 'station-01');
    const updated = updateViewerPreference(preferences, 'heightmap-1', { isCollapsed: true, widthUnits: 99, heightUnits: -1 });

    expect(getViewerPreference(updated, 'heightmap-1')).toEqual({ isCollapsed: true, widthUnits: 12, heightUnits: 3 });
  });
});