import type {
  DashboardPreferences,
  LocalePreferences,
  PhotometricLight,
  ViewerPreference,
  WorkstationPreferences,
} from '../types/workstation-preferences';


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
        outputViewers: {},
        physicalIo: { isCollapsed: false },
        inspectionFlow: { isCollapsed: false },
      },
    },
    locale: {
      language: 'en-US',
      region: 'vi-VN',
      timezone: 'Asia/Ho_Chi_Minh',
      measurementSystem: 'metric',
      clockFormat: '24-hour',
    },
    photometric: {
      lightCount: DEFAULT_LIGHT_COUNT,
      lights: createDefaultLights(DEFAULT_LIGHT_COUNT),
    },
  };
}

export function updateLocalePreference(
  preferences: WorkstationPreferences,
  patch: Partial<LocalePreferences>,
): WorkstationPreferences {
  return {
    ...preferences,
    locale: {
      ...preferences.locale,
      ...patch,
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

export function getViewerPreference(preferences: WorkstationPreferences, viewerKey: string): ViewerPreference {
  return getDashboardViewerPreference(preferences.dashboard, viewerKey);
}

export function updateViewerPreference(
  preferences: WorkstationPreferences,
  viewerKey: string,
  patch: Partial<ViewerPreference>,
): WorkstationPreferences {
  const current = getViewerPreference(preferences, viewerKey);
  const next = updateViewerSize(
    { ...current, isCollapsed: patch.isCollapsed ?? current.isCollapsed },
    patch.widthUnits ?? current.widthUnits,
    patch.heightUnits ?? current.heightUnits,
  );
  return {
    ...preferences,
    dashboard: {
      ...preferences.dashboard,
      panels: {
        ...preferences.dashboard.panels,
        outputViewers: {
          ...preferences.dashboard.panels.outputViewers,
          [viewerKey]: next,
        },
      },
    },
  };
}

export function getDashboardViewerPreference(preferences: DashboardPreferences, viewerKey: string): ViewerPreference {
  return preferences.panels.outputViewers?.[viewerKey]
    ?? preferences.panels.optical2D;
}

export function updateDashboardViewerPreference(
  preferences: DashboardPreferences,
  viewerKey: string,
  viewer: ViewerPreference,
): DashboardPreferences {
  return {
    ...preferences,
    panels: {
      ...preferences.panels,
      outputViewers: {
        ...preferences.panels.outputViewers,
        [viewerKey]: viewer,
      },
    },
  };
}