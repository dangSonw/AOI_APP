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
    physicalIo: PanelPreference;
    inspectionFlow: PanelPreference;
  };
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
  photometric: {
    lightCount: number;
    lights: PhotometricLight[];
  };
}