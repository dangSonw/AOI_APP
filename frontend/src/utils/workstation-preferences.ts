import type { PhotometricLight, ViewerPreference, WorkstationPreferences } from '../types/workstation-preferences';


const DEFAULT_LIGHT_COUNT = 4;

export function createDefaultLights(lightCount: number): PhotometricLight[] {
  return Array.from({ length: lightCount }, (_, index) => ({
    id: index + 1,
    azimuth: Math.round(index * 360 / lightCount) % 360,
    elevation: 25,
    intensity: 82,
  }));
}

export function createDefaultPreferences(userId: number, workstationId: string): WorkstationPreferences {
  return {
    version: 1,
    revision: 0,
    userId,
    workstationId,
    updatedAt: new Date(0).toISOString(),
    dashboard: {
      panels: {
        state: { isCollapsed: false },
        optical2D: { isCollapsed: false, widthUnits: 6, heightUnits: 5 },
        heightmap3D: { isCollapsed: false, widthUnits: 6, heightUnits: 5 },
        physicalIo: { isCollapsed: false },
        inspectionFlow: { isCollapsed: false },
      },
    },
    photometric: {
      lightCount: DEFAULT_LIGHT_COUNT,
      lights: createDefaultLights(DEFAULT_LIGHT_COUNT),
    },
  };
}

export function resizePhotometricLights(current: PhotometricLight[], lightCount: number): PhotometricLight[] {
  const count = Math.min(64, Math.max(1, Math.round(lightCount)));
  const defaults = createDefaultLights(count);
  return defaults.map((light, index) => current[index]
    ? { ...current[index], id: light.id, azimuth: light.azimuth }
    : light);
}

export function updateViewerSize(
  viewer: ViewerPreference,
  widthUnits: number,
  heightUnits: number,
): ViewerPreference {
  return {
    ...viewer,
    widthUnits: Math.min(12, Math.max(3, Math.round(widthUnits))),
    heightUnits: Math.min(12, Math.max(3, Math.round(heightUnits))),
  };
}