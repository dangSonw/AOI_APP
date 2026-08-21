export interface PanelPreference {
  isCollapsed: boolean;
}

export interface ViewerPreference extends PanelPreference {
  widthUnits: number;
  heightUnits: number;
}

export interface DashboardPreferences {
  panels: {
    state: PanelPreference;
    optical2D: ViewerPreference;
    heightmap3D: ViewerPreference;
    outputViewers?: Record<string, ViewerPreference>;
    physicalIo: PanelPreference;
    inspectionFlow: PanelPreference;
  };
}

export interface LocalePreferences {
  language: 'en-US' | 'en-GB';
  region: 'vi-VN' | 'en-SG' | 'de-DE';
  timezone: 'Asia/Ho_Chi_Minh' | 'Asia/Singapore' | 'Europe/Berlin';
  measurementSystem: 'metric' | 'imperial';
  clockFormat: '24-hour' | '12-hour';
}

export interface PhotometricLight {
  id: number;
  azimuth: number;
  elevation: number;
  intensity: number;
}

export interface WorkstationPreferences {
  version: number;
  revision: number;
  userId: number;
  workstationId: string;
  updatedAt: string;
  dashboard: DashboardPreferences;
  locale: LocalePreferences;
  photometric: {
    lightCount: number;
    lights: PhotometricLight[];
  };
}