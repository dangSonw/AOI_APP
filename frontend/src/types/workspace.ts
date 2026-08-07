export type WorkspaceView = 'dashboard' | 'workflow-editor' | 'settings' | 'hardware' | 'camera-manager' | 'database' | 'dataset';

export type InspectionStatus = 'success' | 'warning' | 'error' | 'idle' | 'running';

export interface InspectionRecord {
  boardId: string;
  recipe: string;
  result: 'PASS' | 'REVIEW' | 'FAIL';
  defects: number;
  capturedAt: string;
  lot: string;
}