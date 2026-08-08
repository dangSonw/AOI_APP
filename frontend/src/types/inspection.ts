export interface InspectionDefect {
  id: number;
  defectType: string;
  severity: string;
  locationX: number | null;
  locationY: number | null;
  width: number | null;
  height: number | null;
  confidence: number | null;
  description: string;
  detectedAt: string;
}

export interface InspectionImage {
  id: number;
  imageType: string;
  relativePath: string;
  fileSizeBytes: number | null;
  widthPx: number | null;
  heightPx: number | null;
  sha256Hash: string | null;
  mediaType: string;
  defectId: number | null;
  capturedAt: string;
}

export interface InspectionListItem {
  id: number;
  boardSerial: string;
  lot: string;
  recipeName: string;
  recipeSlug: string;
  result: 'PASS' | 'FAIL' | 'REVIEW';
  defectCount: number;
  score: number | null;
  cycleTimeMs: number | null;
  reviewDecision: string | null;
  inspectedAt: string;
  operatorName: string;
}

export interface InspectionDetail extends InspectionListItem {
  cameraConfig: Record<string, unknown> | null;
  reviewedAt: string | null;
  reviewerName: string | null;
  defects: InspectionDefect[];
  images: InspectionImage[];
}

export interface InspectionMetrics {
  totalInspections: number;
  passCount: number;
  failCount: number;
  reviewCount: number;
  firstPassYield: number;
  totalDefects: number;
  pendingReview: number;
}

export interface InspectionListResponse {
  items: InspectionListItem[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface InspectionFilters {
  page: number;
  pageSize: number;
  result?: string;
  recipeSlug?: string;
  lot?: string;
  search?: string;
}

export interface RecipeItem {
  id: number;
  slug: string;
  name: string;
  description: string;
  isActive: boolean;
}

export type InspectionRunStatus =
  | 'queued'
  | 'precheck'
  | 'capturing'
  | 'executing'
  | 'completed'
  | 'faulted'
  | 'cancelled';

export interface InspectionNodeRun {
  sequence: number;
  nodeId: string;
  nodeVersion: string;
  executionTarget: string;
  status: string;
  parameters: Record<string, unknown>;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  resources: Record<string, unknown>;
  evidenceSha256: string | null;
  errorCode: string | null;
  errorMessage: string | null;
  startedAt: string;
  completedAt: string | null;
  durationMs: number | null;
}

export interface InspectionRun {
  id: string;
  boardSerial: string;
  lot: string;
  recipeId: number;
  resultId: number | null;
  status: InspectionRunStatus;
  currentStep: string;
  progressPercent: number;
  cancelRequested: boolean;
  workflowSha256: string;
  effectiveVersions: Record<string, string>;
  parameters: Record<string, unknown>;
  inputArtifact: Record<string, unknown> | null;
  decision: 'PASS' | 'FAIL' | 'FAULT' | null;
  evidenceSha256: string | null;
  errorCode: string | null;
  errorMessage: string | null;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
  nodeRuns: InspectionNodeRun[];
}

export interface InspectionRunCreate {
  boardSerial: string;
  lot: string;
  recipeId: number;
  threshold: number;
}
