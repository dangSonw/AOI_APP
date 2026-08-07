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

export interface DatasetListResponse {
  datasets: DatasetSummary[];
}

export interface ImageListResponse {
  images: ImageInfo[];
}

export interface CaptureListResponse {
  files: CaptureFile[];
}
