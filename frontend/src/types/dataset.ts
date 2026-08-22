export interface CategorySummary {
  name: string;
  imageCount: number;
  totalSizeBytes: number;
}

export interface DatasetSummary {
  name: string;
  description: string;
  totalImages: number;
  totalSizeBytes: number;
  categoryCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface DatasetDetail extends DatasetSummary {
  categories: CategorySummary[];
}

export interface ImageInfo {
  filename: string;
  sizeBytes: number;
  mediaType: string;
  widthPx: number | null;
  heightPx: number | null;
  createdAt: string;
}

export interface CaptureFile {
  relativePath: string;
  filename: string;
  sizeBytes: number;
}

export interface DatasetValidationIssue {
  categoryName: string;
  filename: string;
  code: string;
  message: string;
}

export interface DatasetValidationReport {
  datasetName: string;
  isValid: boolean;
  categoryCount: number;
  fileCount: number;
  validFileCount: number;
  totalSizeBytes: number;
  duplicateFileCount: number;
  issues: DatasetValidationIssue[];
}

export interface CsvColumnPreview {
  name: string;
  dataType: string;
  missingCount: number;
  uniqueCount: number;
}

export interface CsvPreviewResponse {
  filename: string;
  encoding: string;
  delimiter: string;
  rowCount: number;
  sampleRows: Array<Record<string, string>>;
  truncated: boolean;
  columns: CsvColumnPreview[];
  warnings: string[];
}

export interface CsvPreparationResponse {
  filename: string;
  targetColumn: string;
  featureColumns: string[];
  rowCount: number;
  trainRows: number;
  validationRows: number;
  testRows: number;
  targetDistribution: Record<string, number>;
  warnings: string[];
}

export interface CsvPreparationSnapshotResponse extends CsvPreparationResponse {
  preparationId: string;
  datasetName: string;
  sourceSha256: string;
  configSha256: string;
  createdAt: string;
  preprocessingPolicy: Record<string, string>;
}

export interface CsvPreprocessingPreviewResponse {
  preparationId: string;
  targetColumn: string;
  featureColumns: string[];
  processedColumns: string[];
  trainRows: number;
  validationRows: number;
  testRows: number;
  trainSampleRows: Array<Record<string, string | number>>;
  validationSampleRows: Array<Record<string, string | number>>;
  testSampleRows: Array<Record<string, string | number>>;
  fittedStatistics: Record<string, Record<string, string | number | string[]>>;
  warnings: string[];
}

export interface CsvProcessedArtifactResponse {
  artifactId: string;
  preparationId: string;
  targetColumn: string;
  processedColumns: string[];
  trainRows: number;
  validationRows: number;
  testRows: number;
  splitSha256: Record<string, string>;
  manifestSha256: string;
  createdAt: string;
}

export interface CsvProcessedArtifactVerificationResponse {
  artifactId: string;
  isValid: boolean;
  manifestSha256: string;
  splitSha256: Record<string, string>;
  issues: string[];
}

export interface CsvKnnTrainingJobResponse {
  jobId: string;
  artifactId: string;
  preparationId: string;
  algorithm: string;
  status: string;
  k: number;
  featureColumns: string[];
  targetColumn: string;
  trainRows: number;
  validationAccuracy: number | null;
  testAccuracy: number | null;
  modelSha256: string;
  createdAt: string;
}

export interface DatasetListResponse {
  datasets: DatasetSummary[];
}

export interface ImageListResponse {
  images: ImageInfo[];
}

export interface CaptureListResponse {
  files: CaptureFile[];
}
