export type WorkspaceView = 'dashboard' | 'settings' | 'camera-manager' | 'database';

export type InspectionStatus = 'success' | 'warning' | 'error' | 'idle' | 'running';

export interface InspectionRecord {
  boardId: string;
  recipe: string;
  result: 'PASS' | 'REVIEW' | 'FAIL';
  defects: number;
  capturedAt: string;
  lot: string;
}