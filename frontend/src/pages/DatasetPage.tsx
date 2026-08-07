import { useCallback, useEffect, useRef, useState } from 'react';
import type { CaptureFile, DatasetDetail, DatasetSummary, ImageInfo } from '../types/dataset';
import { NameDialog, type NameDialogKind } from '../components/dataset/NameDialog';
import {
  createCategory,
  createDataset,
  deleteCategory as deleteCategoryService,
  deleteDataset,
  deleteImage,
  exportDataset,
  getImageUrl,
  importCaptures,
  readCaptures,
  readDataset,
  readDatasets,
  readImages,
  renameCategory,
  renameImage,
  updateDataset,
  uploadImages,
} from '../services/dataset-service';


function AuthorizedThumb({
  accessToken,
  url,
  filename,
}: {
  accessToken: string;
  url: string;
  filename: string;
}) {
  const [objectUrl, setObjectUrl] = useState('');

  useEffect(() => {
    let cancelled = false;
    fetch(url, { headers: { Authorization: `Bearer ${accessToken}` } })
      .then((response) => (response.ok ? response.blob() : Promise.reject(new Error('Failed to load image'))))
      .then((blob) => {
        if (!cancelled) setObjectUrl(URL.createObjectURL(blob));
      })
      .catch(() => { /* leave placeholder */ });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [accessToken, url, objectUrl]);

  if (!objectUrl) {
    return <span className="image-grid__thumb image-grid__thumb--placeholder">{filename}</span>;
  }
  return <img className="image-grid__thumb" src={objectUrl} alt={filename} draggable={false} />;
}

function AuthorizedViewerImage({
  accessToken,
  url,
  alt,
}: {
  accessToken: string;
  url: string;
  alt: string;
}) {
  const [objectUrl, setObjectUrl] = useState('');

  useEffect(() => {
    let cancelled = false;
    fetch(url, { headers: { Authorization: `Bearer ${accessToken}` } })
      .then((response) => (response.ok ? response.blob() : Promise.reject(new Error('Failed'))))
      .then((blob) => { if (!cancelled) setObjectUrl(URL.createObjectURL(blob)); })
      .catch(() => { /* noop */ });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [accessToken, url, objectUrl]);

  if (!objectUrl) return <span className="image-viewer__canvas">Loading…</span>;
  return <img className="image-viewer__canvas" src={objectUrl} alt={alt} />;
}


export function DatasetPage({ accessToken }: { accessToken: string }) {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [datasetDetail, setDatasetDetail] = useState<DatasetDetail | null>(null);
  const [images, setImages] = useState<ImageInfo[]>([]);
  const [captures, setCaptures] = useState<CaptureFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [error, setError] = useState('');
  const [viewerImage, setViewerImage] = useState<ImageInfo | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [dialog, setDialog] = useState<
    | { mode: 'create-dataset'; kind: NameDialogKind; showDescription: true }
    | { mode: 'rename-dataset'; kind: NameDialogKind; initialValue: string }
    | { mode: 'create-category'; kind: NameDialogKind }
    | { mode: 'rename-category'; kind: NameDialogKind; initialValue: string }
    | { mode: 'rename-image'; kind: NameDialogKind; initialValue: string }
    | null
  >(null);

  const ease = (ex: unknown) => (ex instanceof Error ? ex.message : 'The request could not be completed.');
  const emptyDetail = (name: string): DatasetDetail => ({
    name, description: '', totalImages: 0, totalSizeBytes: 0, categoryCount: 0,
    createdAt: '', updatedAt: '', categories: [],
  });

  const loadDatasets = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      const list = await readDatasets(accessToken);
      setDatasets(list);
      if (list.length > 0 && !selectedDataset) {
        setSelectedDataset(list[0].name);
        const first = list[0].name;
        setDatasetDetail(await readDataset(accessToken, first));
      }
    } catch (ex) {
      setError(ease(ex));
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, selectedDataset]);

  useEffect(() => { void loadDatasets(); }, [loadDatasets]);

  const loadDetail = useCallback(async (name: string) => {
    setIsDetailLoading(true);
    setError('');
    try {
      setDatasetDetail(await readDataset(accessToken, name));
    } catch (ex) {
      setDatasetDetail(emptyDetail(name));
      setError(ease(ex));
    } finally {
      setIsDetailLoading(false);
    }
  }, [accessToken]);

  const loadImages = useCallback(async (datasetName: string, categoryName: string) => {
    setIsDetailLoading(true);
    setError('');
    try {
      setImages(await readImages(accessToken, datasetName, categoryName));
    } catch (ex) {
      setImages([]);
      setError(ease(ex));
    } finally {
      setIsDetailLoading(false);
    }
  }, [accessToken]);

  const selectDataset = useCallback(async (name: string) => {
    setSelectedDataset(name);
    setSelectedCategory(null);
    setImages([]);
    setViewerImage(null);
    await loadDetail(name);
  }, [loadDetail]);

  const selectCategory = useCallback(async (datasetName: string, categoryName: string) => {
    setSelectedCategory(categoryName);
    setViewerImage(null);
    await Promise.all([loadDetail(datasetName), loadImages(datasetName, categoryName)]);
  }, [loadDetail, loadImages]);

  const refreshCurrent = useCallback(async () => {
    if (!selectedDataset) return;
    await loadDetail(selectedDataset);
    if (selectedCategory) await loadImages(selectedDataset, selectedCategory);
  }, [selectedDataset, selectedCategory, loadDetail, loadImages]);

  const handleCreateDataset = useCallback(async () => {
    setDialog({ mode: 'create-dataset', kind: 'name', showDescription: true });
  }, []);

  const handleCreateCategory = useCallback(async () => {
    if (!selectedDataset) return;
    setDialog({ mode: 'create-category', kind: 'name' });
  }, [selectedDataset]);

  const handleUpload = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    if (!selectedDataset || !selectedCategory) {
      setError('Select a dataset and category before uploading.');
      return;
    }
    try {
      await uploadImages(accessToken, selectedDataset, selectedCategory, Array.from(files));
      await refreshCurrent();
    } catch (ex) { setError(ease(ex)); }
  }, [accessToken, selectedDataset, selectedCategory, refreshCurrent]);

  const handleDeleteImage = useCallback(async (filename: string) => {
    if (!selectedDataset || !selectedCategory) return;
    if (!window.confirm(`Delete image "${filename}"?`)) return;
    try {
      await deleteImage(accessToken, selectedDataset, selectedCategory, filename);
      setViewerImage(null);
      await refreshCurrent();
    } catch (ex) { setError(ease(ex)); }
  }, [accessToken, selectedDataset, selectedCategory, refreshCurrent]);

  const handleRenameImage = useCallback(async (filename: string) => {
    if (!selectedDataset || !selectedCategory) return;
    setDialog({ mode: 'rename-image', kind: 'filename', initialValue: filename });
  }, [selectedDataset, selectedCategory]);

  const handleRenameDataset = useCallback(async () => {
    if (!selectedDataset) return;
    setDialog({ mode: 'rename-dataset', kind: 'name', initialValue: selectedDataset });
  }, [selectedDataset]);

  const handleRenameCategoryAt = useCallback(async (categoryName: string) => {
    if (!selectedDataset) return;
    setDialog({ mode: 'rename-category', kind: 'name', initialValue: categoryName });
  }, [selectedDataset]);

  const handleDeleteDataset = useCallback(async () => {
    if (!selectedDataset) return;
    if (!window.confirm(`Delete dataset "${selectedDataset}" and all its images?`)) return;
    try {
      await deleteDataset(accessToken, selectedDataset);
      setSelectedDataset(null);
      setSelectedCategory(null);
      setDatasetDetail(null);
      setImages([]);
      await loadDatasets();
    } catch (ex) { setError(ease(ex)); }
  }, [accessToken, selectedDataset, loadDatasets]);

  const handleDeleteCategory = useCallback(async (categoryName: string) => {
    if (!selectedDataset) return;
    if (!window.confirm(`Delete category "${categoryName}" and its images?`)) return;
    try {
      setDatasetDetail(await deleteCategoryService(accessToken, selectedDataset, categoryName));
      if (selectedCategory === categoryName) {
        setSelectedCategory(null);
        setImages([]);
      }
    } catch (ex) { setError(ease(ex)); }
  }, [accessToken, selectedDataset, selectedCategory]);

  const handleExport = useCallback(async () => {
    if (!selectedDataset) return;
    try {
      const blob = await exportDataset(accessToken, selectedDataset);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${selectedDataset}.zip`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (ex) { setError(ease(ex)); }
  }, [accessToken, selectedDataset]);

  const handleImport = useCallback(async () => {
    if (!selectedDataset || !selectedCategory) {
      setError('Select a dataset and category before importing captures.');
      return;
    }
    if (captures.length === 0) {
      try { setCaptures(await readCaptures(accessToken)); } catch (ex) { setError(ease(ex)); return; }
    }
    const list = captures.map((c) => c.relativePath).join('\n');
    const input = window.prompt('Paste capture relative paths to import (one per line):\n' + list, list);
    if (!input) return;
    const filenames = input.split('\n').map((x) => x.trim()).filter(Boolean);
    if (filenames.length === 0) return;
    try {
      await importCaptures(accessToken, selectedDataset, filenames, selectedCategory);
      await refreshCurrent();
    } catch (ex) { setError(ease(ex)); }
  }, [accessToken, captures, selectedDataset, selectedCategory, refreshCurrent]);

  const handleDialogSubmit = useCallback(async (value: string, description?: string) => {
    if (!dialog) return;
    const mode = dialog.mode;
    setDialog(null);
    try {
      if (mode === 'create-dataset') {
        await createDataset(accessToken, value, description ?? '');
        setSelectedDataset(value);
        await selectDataset(value);
        await loadDatasets();
      } else if (mode === 'rename-dataset') {
        if (!selectedDataset || value === selectedDataset) return;
        await updateDataset(accessToken, selectedDataset, { newName: value });
        setSelectedDataset(value);
        setDatasetDetail(await readDataset(accessToken, value));
        await loadDatasets();
      } else if (mode === 'create-category') {
        if (!selectedDataset) return;
        setDatasetDetail(await createCategory(accessToken, selectedDataset, value));
      } else if (mode === 'rename-category') {
        if (!selectedDataset) return;
        const oldName = dialog.initialValue;
        setDatasetDetail(await renameCategory(accessToken, selectedDataset, oldName, value));
        if (selectedCategory === oldName) setSelectedCategory(value);
      } else if (mode === 'rename-image') {
        if (!selectedDataset || !selectedCategory) return;
        const oldName = dialog.initialValue;
        if (value === oldName) return;
        await renameImage(accessToken, selectedDataset, selectedCategory, oldName, value);
        await refreshCurrent();
      }
    } catch (ex) { setError(ease(ex)); }
  }, [dialog, accessToken, selectedDataset, selectedCategory, selectDataset, loadDatasets, refreshCurrent]);


  const viewerIndex = viewerImage ? images.findIndex((i) => i.filename === viewerImage.filename) : -1;
  const showPrev = () => {
    if (!viewerImage || images.length === 0) return;
    const next = images[(viewerIndex - 1 + images.length) % images.length];
    setViewerImage(next);
  };
  const showNext = () => {
    if (!viewerImage || images.length === 0) return;
    const next = images[(viewerIndex + 1) % images.length];
    setViewerImage(next);
  };

  const formatBytes = (bytes: number) => {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    return `${(bytes / (1024 ** i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
  };

  const totalSize = datasets.reduce((sum, d) => sum + d.totalSizeBytes, 0);
  const totalImagesCount = datasets.reduce((sum, d) => sum + d.totalImages, 0);
  const currentThumbUrl = selectedDataset && selectedCategory && viewerImage
    ? getImageUrl(selectedDataset, selectedCategory, viewerImage.filename)
    : '';

  return (
    <div className="dataset-page">
      <aside className="dataset-browser">
        <div className="panel-heading"><span>Datasets</span></div>
        <button type="button" className="studio-primary-button dataset-browser__new" onClick={handleCreateDataset}>
          + New dataset
        </button>
        {isLoading ? (
          <p className="dataset-browser__empty">Loading…</p>
        ) : datasets.length === 0 ? (
          <p className="dataset-browser__empty">No datasets yet.</p>
        ) : (
          <ul className="dataset-browser__list">
            {datasets.map((dataset) => {
              const isActive = dataset.name === selectedDataset;
              const detail = isActive ? datasetDetail : null;
              return (
                <li key={dataset.name} className="dataset-browser__dataset">
                  <button
                    type="button"
                    className={`dataset-browser__row ${isActive ? 'dataset-browser__row--active' : ''}`}
                    onClick={() => void selectDataset(dataset.name)}
                  >
                    <span className="dataset-browser__label">{dataset.name}</span>
                    <span className="dataset-browser__meta">{dataset.totalImages} img</span>
                  </button>
                  {isActive && (
                    <div className="dataset-browser__actions">
                      <button type="button" onClick={handleRenameDataset}>Rename</button>
                      <button type="button" onClick={handleDeleteDataset}>Delete</button>
                      <button type="button" onClick={handleExport}>Export</button>
                    </div>
                  )}
                  {isActive && (
                    <ul className="dataset-browser__categories">
                      {(detail?.categories ?? []).map((category) => {
                        const catActive = category.name === selectedCategory;
                        return (
                          <li key={category.name}>
                            <button
                              type="button"
                              className={`dataset-browser__category ${catActive ? 'dataset-browser__category--active' : ''}`}
                              onClick={() => void selectCategory(dataset.name, category.name)}
                            >
                              {category.name} ({category.imageCount})
                            </button>
                            {catActive && (
                              <div className="dataset-browser__actions">
                                <button type="button" onClick={() => void handleRenameCategoryAt(category.name)}>Rename</button>
                                <button type="button" onClick={() => void handleDeleteCategory(category.name)}>Delete</button>
                              </div>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                  {isActive && (
                    <button type="button" className="dataset-browser__add-category" onClick={handleCreateCategory}>
                      + Category
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </aside>

      <section className="dataset-content">
        <div className="dataset-toolbar">
          <h2 className="dataset-toolbar__title">
            {selectedDataset ? selectedDataset : 'Dataset manager'}
            {selectedCategory ? ` / ${selectedCategory}` : ''}
          </h2>
          <div className="dataset-toolbar__actions">
            <input
              ref={fileInputRef}
              type="file"
              accept=".png,.jpg,.jpeg,.bmp,.tiff,.tif"
              multiple
              hidden
              onChange={(event) => void handleUpload(event.target.files)}
            />
            <button
              type="button"
              disabled={!selectedDataset || !selectedCategory}
              onClick={() => fileInputRef.current?.click()}
            >
              Upload
            </button>
            <button type="button" disabled={!selectedDataset || !selectedCategory} onClick={handleImport}>
              Import captures
            </button>
          </div>
        </div>

        {error && <div className="dataset-page__error">{error}</div>}

        <div className="image-grid">
          {isDetailLoading && images.length === 0 && <p className="image-grid__empty">Loading images…</p>}
          {!isDetailLoading && !selectedCategory && (
            <p className="image-grid__empty">Select a category to view its images.</p>
          )}
          {!isDetailLoading && selectedCategory && images.length === 0 && (
            <p className="image-grid__empty">No images in this category. Upload or import some.</p>
          )}
          {images.map((image) => (
            <div className="image-grid__item" key={image.filename}>
              <button
                type="button"
                className="image-grid__thumb-button"
                onClick={() => setViewerImage(image)}
                aria-label={`View ${image.filename}`}
              >
                <AuthorizedThumb
                  accessToken={accessToken}
                  url={getImageUrl(selectedDataset!, selectedCategory!, image.filename)}
                  filename={image.filename}
                />
              </button>
              <span className="image-grid__label" title={image.filename}>{image.filename}</span>
              <div className="image-grid__actions">
                <button type="button" onClick={() => void handleRenameImage(image.filename)}>Rename</button>
                <button type="button" onClick={() => void handleDeleteImage(image.filename)}>Delete</button>
              </div>
            </div>
          ))}
        </div>

        <footer className="dataset-status">
          <span>
            {datasets.length} dataset{datasets.length === 1 ? '' : 's'} · {totalImagesCount} images · {formatBytes(totalSize)} total
          </span>
        </footer>
      </section>

      {viewerImage && selectedDataset && selectedCategory && (
        <div className="image-viewer-overlay" role="dialog" aria-modal="true" aria-label="Image viewer">
          <div className="image-viewer">
            <div className="image-viewer__header">
              <span className="image-viewer__name">{viewerImage.filename}</span>
              <span className="image-viewer__meta">
                {viewerImage.widthPx && viewerImage.heightPx
                  ? `${viewerImage.widthPx} × ${viewerImage.heightPx}`
                  : ''} · {formatBytes(viewerImage.sizeBytes)}
              </span>
              <button type="button" className="image-viewer__close" onClick={() => setViewerImage(null)}>✕</button>
            </div>
            <AuthorizedViewerImage
              accessToken={accessToken}
              url={currentThumbUrl}
              alt={viewerImage.filename}
            />
            <div className="image-viewer__footer">
              <button type="button" onClick={showPrev} disabled={images.length <= 1}>← Prev</button>
              <span>{viewerIndex + 1} / {images.length}</span>
              <button type="button" onClick={showNext} disabled={images.length <= 1}>Next →</button>
              <button type="button" onClick={() => void handleDeleteImage(viewerImage.filename)}>Delete</button>
            </div>
          </div>
        </div>
      )}

      {dialog && (() => {
        if (dialog.mode === 'create-dataset') {
          return (
            <NameDialog
              title="New dataset"
              label="Dataset name"
              placeholder="e.g. golden-samples"
              helper="Lowercase letters, numbers and hyphens (kebab-case)."
              showDescription
              descriptionLabel="Description (optional)"
              descriptionPlaceholder="e.g. Golden reference images for Rev C mainboard"
              confirmLabel="Create dataset"
              onCancel={() => setDialog(null)}
              onSubmit={(value, description) => void handleDialogSubmit(value, description)}
            />
          );
        }
        if (dialog.mode === 'rename-dataset') {
          return (
            <NameDialog
              title="Rename dataset"
              label="Dataset name"
              placeholder="e.g. golden-samples"
              helper="Lowercase letters, numbers and hyphens (kebab-case)."
              initialValue={dialog.initialValue}
              confirmLabel="Rename"
              onCancel={() => setDialog(null)}
              onSubmit={(value) => void handleDialogSubmit(value)}
            />
          );
        }
        if (dialog.mode === 'create-category') {
          return (
            <NameDialog
              title="New folder"
              label="Folder name"
              placeholder="e.g. top-view"
              helper="Lowercase letters, numbers and hyphens (kebab-case)."
              confirmLabel="Create folder"
              onCancel={() => setDialog(null)}
              onSubmit={(value) => void handleDialogSubmit(value)}
            />
          );
        }
        if (dialog.mode === 'rename-category') {
          return (
            <NameDialog
              title="Rename folder"
              label="Folder name"
              placeholder="e.g. top-view"
              helper="Lowercase letters, numbers and hyphens (kebab-case)."
              initialValue={dialog.initialValue}
              confirmLabel="Rename folder"
              onCancel={() => setDialog(null)}
              onSubmit={(value) => void handleDialogSubmit(value)}
            />
          );
        }
        return (
          <NameDialog
            title="Rename image"
            label="Filename"
            kind="filename"
            placeholder="e.g. img001.png"
            helper={'Letters, numbers, "-" or "_" with an image extension.'}
            initialValue={dialog.initialValue}
            confirmLabel="Rename"
            onCancel={() => setDialog(null)}
            onSubmit={(value) => void handleDialogSubmit(value)}
          />
        );
      })()}
    </div>
  );
}




