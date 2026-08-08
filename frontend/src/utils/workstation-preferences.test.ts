import { describe, expect, it } from 'vitest';
import {
  createDefaultPreferences,
  resizePhotometricLights,
  updateLocalePreference,
  updateViewerSize,
} from './workstation-preferences';


describe('workstation preference helpers', () => {
  it('creates one evenly spaced capture configuration per light', () => {
    const preferences = createDefaultPreferences(3, 'station-01');

    expect(preferences.locale).toEqual({
      language: 'en-US',
      region: 'vi-VN',
      timezone: 'Asia/Ho_Chi_Minh',
      measurementSystem: 'metric',
      clockFormat: '24-hour',
    });
    expect(preferences.photometric.lightCount).toBe(4);
    expect(preferences.photometric.lights.map((light) => light.azimuth)).toEqual([0, 90, 180, 270]);
  });

  it('updates one locale preference without changing workstation identity', () => {
    const preferences = createDefaultPreferences(3, 'station-01');

    const updated = updateLocalePreference(preferences, {
      language: 'en-GB',
      measurementSystem: 'imperial',
    });

    expect(updated.workstationId).toBe('station-01');
    expect(updated.locale.language).toBe('en-GB');
    expect(updated.locale.measurementSystem).toBe('imperial');
    expect(updated.locale.timezone).toBe('Asia/Ho_Chi_Minh');
  });

  it('keeps image count equal to light count when resizing the rig', () => {
    const current = createDefaultPreferences(3, 'station-01').photometric.lights;
    const resized = resizePhotometricLights(current, 6);

    expect(resized).toHaveLength(6);
    expect(resized.map((light) => light.azimuth)).toEqual([0, 60, 120, 180, 240, 300]);
    expect(resizePhotometricLights(resized, 2)).toHaveLength(2);
  });

  it('clamps viewer dimensions to responsive layout bounds', () => {
    const viewer = updateViewerSize({ isCollapsed: false, widthUnits: 6, heightUnits: 5 }, 99, -4);

    expect(viewer.widthUnits).toBe(12);
    expect(viewer.heightUnits).toBe(3);
  });
});