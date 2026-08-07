# Dataset Manager Implementation Plan

**Date:** 2026-08-07  
**Spec:** `specs/2026-08-07-dataset-manager-design.md`  
**Goal:** Deliver full dataset management: file-based storage, backend API, frontend DatasetPage with image viewer.

---

## Phase 1: Backend Foundation

### Task 1.1: Add settings and create data directory

**File:** `backend/app/config/settings.py`  
**Action:** Add `datasets_data_directory` field and `datasets_data_path` property.

```python
datasets_data_directory: str = 'data/datasets'

@property
def datasets_data_path(self) -> Path:
    return PROJECT_ROOT / self.datasets_data_directory
```

**Pitfall (WSL):** Ensure `data/datasets/` directory exists. Create with `mkdir -p` in setup or auto-create in service layer. Do NOT use absolute paths.

**Verification:** Import settings, confirm `datasets_data_path` resolves correctly relative to PROJECT_ROOT.

---

### Task 1.2: Create Pydantic schemas

**File:** `backend/app/schemas/dataset.py`  
**Action:** Create all request/response schemas.

Schemas to create:
- `DatasetCreateRequest` — name (kebab-case validated), description
- `DatasetUpdateRequest` — optional new_name, description
- `CategoryCreateRequest` — name
- `CategoryRenameRequest` — new_name
- `ImageRenameRequest` — new_filename
- `ImageMoveRequest` — target_category
- `ImportCapturesRequest` — filenames list, target_category
- `CategorySummary` — name, image_count, total_size_bytes
- `DatasetSummary` — name, description, total_images, total_size_bytes, category_count, created_at, updated_at
- `DatasetDetail` — extends summary with categories list
- `ImageInfo` — filename, size_bytes, media_type, width_px, height_px, created_at
- `ImageListResponse` — images list

**Validation rules:**
- Name fields: `Field(min_length=1, max_length=64, pattern=r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')`
- Single char names allowed: adjust regex to `r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'`
- Filename: `Field(max_length=128)` + custom validator for safe chars and extension

**Pitfall:** Pydantic v2 uses `pattern` not `regex`. Project uses pydantic-settings, confirm v2.

---

### Task 1.3: Create dataset service

**File:** `backend/app/services/dataset_service.py`  
**Action:** All filesystem operations.

Functions to implement (in order):

1. `_validate_name(name: str) -> None` — regex check, reject unsafe
2. `_validate_filename(filename: str) -> None` — extension + safe chars
3. `_get_datasets_root() -> Path` — returns `settings.datasets_data_path`, creates if missing
4. `_get_dataset_path(name: str) -> Path` — validates + resolves
5. `_read_image_dimensions(file_path: Path) -> tuple[int | None, int | None]` — struct-based PNG/JPEG header parsing
6. `_regenerate_metadata(dataset_path: Path) -> dict` — scan dirs, count files, write metadata.json atomically
7. `list_datasets() -> list[dict]` — scan root dir, read each metadata.json
8. `create_dataset(name: str, description: str) -> dict` — mkdir + metadata
9. `get_dataset(name: str) -> dict` — read metadata
10. `update_dataset(name: str, new_name: str | None, description: str | None) -> dict` — rename dir if needed
11. `delete_dataset(name: str) -> None` — shutil.rmtree
12. `create_category(dataset_name: str, category_name: str) -> dict`
13. `rename_category(dataset_name: str, old_name: str, new_name: str) -> dict`
14. `delete_category(dataset_name: str, category_name: str) -> dict`
15. `list_images(dataset_name: str, category_name: str) -> list[dict]`
16. `upload_images(dataset_name: str, category_name: str, files: list[UploadFile]) -> list[dict]`
17. `get_image_path(dataset_name: str, category_name: str, filename: str) -> Path`
18. `delete_image(dataset_name: str, category_name: str, filename: str) -> None`
19. `rename_image(dataset_name: str, category_name: str, old_name: str, new_name: str) -> dict`
20. `move_image(dataset_name: str, category_name: str, filename: str, target_category: str) -> dict`
21. `import_captures(dataset_name: str, filenames: list[str], target_category: str) -> list[dict]`
22. `export_dataset_zip(dataset_name: str) -> Path` — creates temp zip, returns path
23. `list_captures() -> list[dict]` — scan data/captures/ recursively for images

**Critical pitfalls:**
- ALWAYS validate path segments before joining to filesystem path. Never trust user input.
- Use `os.replace()` for atomic metadata.json writes (temp file first).
- `shutil.rmtree` for delete — confirm path is inside datasets root before calling.
- Image upload: read into memory bounded by 50MB limit per file; write atomically.
- Capture import: `shutil.copy2` from `data/captures/` to dataset — validate source path is inside captures root.
- For image dimensions: parse PNG IHDR chunk (bytes 16-24) or JPEG SOF marker. Catch all exceptions, return None on failure.

**WSL pitfall:** Do NOT use `os.path.sep` — always use `pathlib.Path` which handles `/` correctly on all platforms.

---

### Task 1.4: Create API router

**File:** `backend/app/api/datasets.py`  
**Action:** FastAPI router with all endpoints.

```python
router = APIRouter(prefix='/api/datasets', tags=['datasets'])
```

Endpoints (map directly from spec section 3):

1. `GET /api/datasets` → `list_datasets()`
2. `POST /api/datasets` → `create_dataset(request)`
3. `GET /api/datasets/{name}` → `get_dataset(name)`
4. `PUT /api/datasets/{name}` → `update_dataset(name, request)`
5. `DELETE /api/datasets/{name}` → `delete_dataset(name)`
6. `POST /api/datasets/{name}/categories` → `create_category(name, request)`
7. `PUT /api/datasets/{name}/categories/{category}` → `rename_category(name, category, request)`
8. `DELETE /api/datasets/{name}/categories/{category}` → `delete_category(name, category)`
9. `GET /api/datasets/{name}/categories/{category}/images` → `list_images(name, category)`
10. `POST /api/datasets/{name}/categories/{category}/images` → upload (multipart, `File(...)`)
11. `GET /api/datasets/{name}/categories/{category}/images/{filename}` → `FileResponse`
12. `DELETE /api/datasets/{name}/categories/{category}/images/{filename}` → delete
13. `PATCH /api/datasets/{name}/categories/{category}/images/{filename}` → rename
14. `POST /api/datasets/{name}/categories/{category}/images/{filename}/move` → move
15. `POST /api/datasets/{name}/import-captures` → import
16. `GET /api/datasets/{name}/export` → StreamingResponse with ZIP

Separate router for captures:
```python
captures_router = APIRouter(prefix='/api/captures', tags=['captures'])
```
17. `GET /api/captures` → list capture files

**Image serving:** Use `FileResponse` with `media_type` detected from extension. Set `Cache-Control: private, max-age=3600`.

**Upload:** Accept `List[UploadFile]` via `files: list[UploadFile] = File(...)`. Validate each file size, extension, magic bytes before writing.

**Export:** Stream ZIP using generator + `StreamingResponse(content, media_type='application/zip', headers={'Content-Disposition': ...})`.

**Pitfall:** FastAPI `UploadFile` reads into memory by default. For large files, use `file.read(chunk_size)` in a loop with size tracking to enforce 50MB limit without loading entire file at once.

---

### Task 1.5: Register routers in main.py

**File:** `backend/app/main.py`  
**Action:** Add two imports and two `app.include_router()` calls.

```python
from app.api.datasets import router as datasets_router
from app.api.datasets import captures_router

app.include_router(datasets_router)
app.include_router(captures_router)
```

**Verification:** Start backend, confirm `/docs` shows all new endpoints.

---

## Phase 2: Frontend Foundation

### Task 2.1: Create TypeScript types

**File:** `frontend/src/types/dataset.ts`  
**Action:** Define interfaces matching backend schemas.

```typescript
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
```

---

### Task 2.2: Create API service

**File:** `frontend/src/services/dataset-service.ts`  
**Action:** API client functions using existing `apiRequest` and `apiBlobRequest`.

Functions:
- `readDatasets(accessToken)` → GET /api/datasets
- `createDataset(accessToken, name, description)` → POST /api/datasets
- `readDataset(accessToken, name)` → GET /api/datasets/{name}
- `updateDataset(accessToken, name, body)` → PUT /api/datasets/{name}
- `deleteDataset(accessToken, name)` → DELETE /api/datasets/{name}
- `createCategory(accessToken, datasetName, categoryName)` → POST .../categories
- `renameCategory(accessToken, datasetName, oldName, newName)` → PUT .../categories/{old}
- `deleteCategory(accessToken, datasetName, categoryName)` → DELETE .../categories/{name}
- `readImages(accessToken, datasetName, categoryName)` → GET .../images
- `uploadImages(accessToken, datasetName, categoryName, files: File[])` → POST multipart
- `getImageUrl(datasetName, categoryName, filename)` → returns URL string (no fetch, used for img src)
- `deleteImage(accessToken, datasetName, categoryName, filename)` → DELETE
- `renameImage(accessToken, datasetName, categoryName, oldName, newName)` → PATCH
- `moveImage(accessToken, datasetName, categoryName, filename, targetCategory)` → POST .../move
- `importCaptures(accessToken, datasetName, filenames, targetCategory)` → POST .../import-captures
- `exportDataset(accessToken, datasetName)` → GET .../export (blob download)
- `readCaptures(accessToken)` → GET /api/captures

**Upload pitfall:** `uploadImages` must use `FormData`, NOT JSON. Do NOT set Content-Type header manually — browser sets multipart boundary automatically.

```typescript
export async function uploadImages(
  accessToken: string,
  datasetName: string,
  categoryName: string,
  files: File[],
): Promise<ImageInfo[]> {
  const formData = new FormData();
  for (const file of files) formData.append('files', file);
  const headers = new Headers({ Authorization: `Bearer ${accessToken}` });
  // Do NOT set Content-Type — browser adds multipart boundary
  const response = await fetch(`${API_BASE_URL}/api/datasets/${datasetName}/categories/${categoryName}/images`, {
    method: 'POST', headers, body: formData,
  });
  // ... error handling same pattern as apiRequest
}
```

**Image URL pitfall:** For `<img src>`, need auth header. Two approaches:
- Option A: Fetch blob + `URL.createObjectURL()` (works everywhere, uses memory)
- Option B: Backend generates short-lived token-in-URL (complex)
- **Choose Option A** for simplicity. Cache blob URLs, revoke on unmount.

---

### Task 2.3: Update workspace types

**File:** `frontend/src/types/workspace.ts`  
**Action:** Add `'dataset'` to WorkspaceView union.

Change line 1 from:
```typescript
export type WorkspaceView = 'dashboard' | 'workflow-editor' | 'settings' | 'hardware' | 'camera-manager' | 'database';
```
To:
```typescript
export type WorkspaceView = 'dashboard' | 'workflow-editor' | 'settings' | 'hardware' | 'camera-manager' | 'database' | 'dataset';
```

---

### Task 2.4: Update ProjectExplorer

**File:** `frontend/src/components/ProjectExplorer.tsx`  
**Action:** Add `view: 'dataset'` to the Dataset item in EXPLORER_ITEMS.

Change line 21 from:
```typescript
{ label: 'Dataset', icon: 'D' },
```
To:
```typescript
{ label: 'Dataset', icon: 'D', view: 'dataset' },
```

---

### Task 2.5: Update WorkspacePage

**File:** `frontend/src/pages/WorkspacePage.tsx`  
**Action:** Import DatasetPage, add view title, render conditionally.

1. Add import: `import { DatasetPage } from './DatasetPage';`
2. Add to `viewTitles`: `'dataset': 'Dataset manager'`
3. Add render: `{activeView === 'dataset' && <DatasetPage accessToken={session.accessToken} />}`

Place the render line after the database line (line 211).

---

## Phase 3: Frontend Components

### Task 3.1: Create DatasetPage.tsx

**File:** `frontend/src/pages/DatasetPage.tsx`  
**Action:** Main page component, orchestrates all child components.

State:
- `datasets: DatasetSummary[]` — loaded from API
- `selectedDataset: string | null` — current dataset name
- `selectedCategory: string | null` — current category
- `datasetDetail: DatasetDetail | null` — loaded on dataset select
- `images: ImageInfo[]` — loaded on category select
- `isLoading, error` — standard loading/error state
- `viewerImage: ImageInfo | null` — which image is open in viewer

Layout: flex row — DatasetBrowser (left 240px) + main content area (flex 1).
Main content: DatasetToolbar (top) + ImageGrid (center) + status bar (bottom).

**Pitfall:** Avoid re-fetching entire dataset list on every small mutation. After upload/delete/move, refetch only the affected dataset detail and image list.

---

### Task 3.2: Create DatasetBrowser.tsx

**File:** `frontend/src/components/dataset/DatasetBrowser.tsx`  
**Action:** Left sidebar tree view.

Props:
- `datasets: DatasetSummary[]`
- `selectedDataset: string | null`
- `selectedCategory: string | null`
- `datasetDetail: DatasetDetail | null`
- `onSelectDataset: (name: string) => void`
- `onSelectCategory: (datasetName: string, categoryName: string) => void`
- `onCreateDataset: () => void`
- `onCreateCategory: (datasetName: string) => void`
- `onRenameDataset: (name: string) => void`
- `onRenameCategory: (datasetName: string, categoryName: string) => void`
- `onDeleteDataset: (name: string) => void`
- `onDeleteCategory: (datasetName: string, categoryName: string) => void`

Render: collapsible tree. Each dataset expands to show categories. Context menu (right-click) for rename/delete/new category.

**CSS:** Use existing `project-tree` styles as reference. Light theme. No position:absolute for layout.

---

### Task 3.3: Create ImageGrid.tsx

**File:** `frontend/src/components/dataset/ImageGrid.tsx`  
**Action:** Responsive thumbnail grid.

Props:
- `images: ImageInfo[]`
- `datasetName: string`
- `categoryName: string`
- `accessToken: string`
- `onImageClick: (image: ImageInfo) => void`
- `onDeleteImage: (filename: string) => void`
- `onRenameImage: (filename: string) => void`

Each thumbnail:
- Load image via blob fetch with auth header
- Show filename below
- Show file size
- Click opens ImageViewer
- Right-click context menu: rename, delete, move

Grid: CSS Grid with `grid-template-columns: repeat(auto-fill, minmax(160px, 1fr))`.

**Pitfall:** Blob URLs must be revoked when component unmounts or images change. Use `useEffect` cleanup. Keep a Map of filename → blobUrl in a ref.

**Drag-drop upload:** Add `onDragOver`, `onDrop` handlers on the grid container. Extract files from `DataTransfer`, call upload function.

---

### Task 3.4: Create ImageViewer.tsx

**File:** `frontend/src/components/dataset/ImageViewer.tsx`  
**Action:** Full-screen modal with zoom and pan.

Props:
- `image: ImageInfo`
- `images: ImageInfo[]` (for prev/next navigation)
- `datasetName: string`
- `categoryName: string`
- `accessToken: string`
- `onClose: () => void`
- `onDelete: (filename: string) => void`
- `onNavigate: (image: ImageInfo) => void`

Implementation:
- Modal overlay with dark backdrop
- Image loaded via blob URL (reuse from grid if cached)
- Zoom: CSS `transform: scale(zoomLevel)`. Scroll wheel handler with `preventDefault()`.
- Pan: `transform: translate(panX, panY)`. Mouse down starts drag, mouse move updates translation, mouse up stops.
- State: `zoomLevel` (default: fit-to-container), `panX`, `panY`, `isDragging`
- Reset zoom/pan on image change
- Prev/Next: find current index in images array, navigate

**Keyboard:**
- `Escape` → close
- `ArrowLeft` → prev image
- `ArrowRight` → next image
- `+` / `=` → zoom in
- `-` → zoom out
- `0` → reset zoom

**Pitfall:** Prevent body scroll when modal is open. Add `overflow: hidden` to body on mount, restore on unmount.

---

### Task 3.5: Create DatasetToolbar.tsx

**File:** `frontend/src/components/dataset/DatasetToolbar.tsx`  
**Action:** Top toolbar with action buttons.

Props:
- `selectedDataset: string | null`
- `selectedCategory: string | null`
- `onUpload: (files: File[]) => void`
- `onImportCaptures: () => void`
- `onExport: () => void`
- `onCreateDataset: () => void`

Buttons:
- [+ New Dataset] — always enabled
- [Upload] — enabled when category selected, opens file picker (accept="image/*")
- [Import from Captures] — enabled when category selected, opens capture picker dialog
- [Export ZIP] — enabled when dataset selected
- Breadcrumb: "dataset-name / category-name" showing current location

Hidden file input for upload: `<input type="file" multiple accept=".png,.jpg,.jpeg,.bmp,.tiff,.tif" />`

---

## Phase 4: Styling

### Task 4.1: Add dataset CSS

**Action:** Add dataset styles to existing stylesheet (find main CSS file).

Key classes:
- `.dataset-page` — flex row, full height
- `.dataset-browser` — left panel, 240px width, overflow-y auto
- `.dataset-content` — flex 1, flex column
- `.dataset-toolbar` — flex row, gap, padding, border-bottom
- `.image-grid` — CSS Grid, gap 12px, padding
- `.image-grid__item` — border, border-radius, overflow hidden, cursor pointer
- `.image-grid__thumb` — object-fit cover, aspect-ratio 1
- `.image-grid__label` — text below thumb, truncate
- `.image-viewer-overlay` — fixed overlay, z-index 1000, dark backdrop
- `.image-viewer` — centered, max 90vw/90vh
- `.image-viewer__canvas` — overflow hidden, cursor grab/grabbing

Follow RULE.md section 15: light theme, WCAG AA contrast, responsive from 320px up.

---

## Phase 5: Integration and Testing

### Task 5.1: Backend tests

**File:** `tests/backend/test_dataset_service.py`  
- Test create/list/get/update/delete dataset
- Test create/rename/delete category
- Test upload/list/delete/rename/move images
- Test path traversal rejection
- Test file size limit
- Test invalid names rejected
- Test metadata.json regeneration accuracy

### Task 5.2: API integration tests

**File:** `tests/backend/test_dataset_api.py`  
- Test all endpoints with auth
- Test 401 without token
- Test 404 for missing dataset/category
- Test 422 for invalid names
- Test multipart upload
- Test ZIP export download

### Task 5.3: Final verification checklist

- [ ] Create dataset from UI
- [ ] Create categories within dataset
- [ ] Upload images via file picker
- [ ] Upload images via drag-and-drop
- [ ] Thumbnails load with auth
- [ ] Click thumbnail opens viewer
- [ ] Zoom and pan work in viewer
- [ ] Arrow keys navigate images
- [ ] Rename dataset, category, image
- [ ] Delete image, category, dataset (with confirmation)
- [ ] Move image between categories
- [ ] Import from captures
- [ ] Export ZIP downloads correctly
- [ ] metadata.json updates after each operation
- [ ] Responsive layout at 390px, 768px, 1280px, 1920px
- [ ] No absolute paths in any code
- [ ] No horizontal overflow at any viewport width
- [ ] Works on WSL Ubuntu

---

## Execution Order Summary

| Step | Phase | Task | Files |
|------|-------|------|-------|
| 1 | 1.1 | Settings | `backend/app/config/settings.py` |
| 2 | 1.2 | Schemas | `backend/app/schemas/dataset.py` |
| 3 | 1.3 | Service | `backend/app/services/dataset_service.py` |
| 4 | 1.4 | API Router | `backend/app/api/datasets.py` |
| 5 | 1.5 | Register | `backend/app/main.py` |
| 6 | 2.1 | TS Types | `frontend/src/types/dataset.ts` |
| 7 | 2.2 | TS Service | `frontend/src/services/dataset-service.ts` |
| 8 | 2.3 | Workspace type | `frontend/src/types/workspace.ts` |
| 9 | 2.4 | Explorer | `frontend/src/components/ProjectExplorer.tsx` |
| 10 | 2.5 | WorkspacePage | `frontend/src/pages/WorkspacePage.tsx` |
| 11 | 3.1 | DatasetPage | `frontend/src/pages/DatasetPage.tsx` |
| 12 | 3.2 | Browser | `frontend/src/components/dataset/DatasetBrowser.tsx` |
| 13 | 3.3 | Grid | `frontend/src/components/dataset/ImageGrid.tsx` |
| 14 | 3.4 | Viewer | `frontend/src/components/dataset/ImageViewer.tsx` |
| 15 | 3.5 | Toolbar | `frontend/src/components/dataset/DatasetToolbar.tsx` |
| 16 | 4.1 | CSS | Main stylesheet |
| 17 | 5.1-5.3 | Tests | `tests/backend/` |

Each step depends on previous steps. Do NOT skip ahead. Verify each step compiles/runs before proceeding.
