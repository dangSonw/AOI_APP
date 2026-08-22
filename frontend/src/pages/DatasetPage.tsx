import { useCallback, useEffect, useRef, useState } from 'react';
import type { CaptureFile, CsvKnnTrainingJobResponse, CsvPreparationResponse, CsvPreparationSnapshotResponse, CsvPreprocessingPreviewResponse, CsvProcessedArtifactResponse, CsvProcessedArtifactVerificationResponse, CsvPreviewResponse, DatasetDetail, DatasetSummary, DatasetValidationReport, ImageInfo } from '../types/dataset';
import { NameDialog, type NameDialogKind } from '../components/dataset/NameDialog';
import { DatasetBrowser } from '../components/dataset/DatasetBrowser';
import { DatasetImageGrid } from '../components/dataset/DatasetImageGrid';
import { DatasetImageViewer } from '../components/dataset/DatasetImageViewer';
import {
  createCategory,
  createDataset,
  createCsvPreparationSnapshot,
  createCsvProcessedArtifact,
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
  validateDataset,
  previewCsv,
  prepareCsv,
  previewCsvPreprocessing,
  readCsvProcessedArtifacts,
  verifyCsvProcessedArtifact,
  createCsvKnnTrainingJob,
  readCsvKnnTrainingJobs,
} from '../services/dataset-service';


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
  const [validationReport, setValidationReport] = useState<DatasetValidationReport | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [csvPreview, setCsvPreview] = useState<CsvPreviewResponse | null>(null);
  const [isPreviewingCsv, setIsPreviewingCsv] = useState(false);
  const [csvPreparation, setCsvPreparation] = useState<CsvPreparationResponse | null>(null);
  const [csvTargetColumn, setCsvTargetColumn] = useState('');
  const [csvFeatureColumns, setCsvFeatureColumns] = useState<string[]>([]);
  const [csvSplit, setCsvSplit] = useState({ train: 0.7, validation: 0.15, test: 0.15 });
  const [isPreparingCsv, setIsPreparingCsv] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvSnapshot, setCsvSnapshot] = useState<CsvPreparationSnapshotResponse | null>(null);
  const [isCreatingCsvSnapshot, setIsCreatingCsvSnapshot] = useState(false);
  const [csvPolicy, setCsvPolicy] = useState({ numeric_missing: 'error', categorical_missing: 'error', scaling: 'none', categorical_encoding: 'none' });
  const [csvProcessedPreview, setCsvProcessedPreview] = useState<CsvPreprocessingPreviewResponse | null>(null);
  const [isPreviewingProcessedCsv, setIsPreviewingProcessedCsv] = useState(false);
  const [csvArtifact, setCsvArtifact] = useState<CsvProcessedArtifactResponse | null>(null);
  const [isCreatingCsvArtifact, setIsCreatingCsvArtifact] = useState(false);
  const [csvArtifacts, setCsvArtifacts] = useState<CsvProcessedArtifactResponse[]>([]);
  const [csvArtifactVerification, setCsvArtifactVerification] = useState<CsvProcessedArtifactVerificationResponse | null>(null);
  const [isVerifyingCsvArtifact, setIsVerifyingCsvArtifact] = useState(false);
  const [csvKnnK, setCsvKnnK] = useState(3);
  const [csvKnnJobs, setCsvKnnJobs] = useState<CsvKnnTrainingJobResponse[]>([]);
  const [isTrainingCsvKnn, setIsTrainingCsvKnn] = useState(false);
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
    setValidationReport(null);
    setCsvPreview(null);
    setCsvPreparation(null);
    setCsvSnapshot(null);
    setCsvProcessedPreview(null);
    setCsvArtifact(null);
    setCsvArtifacts([]);
    setCsvArtifactVerification(null);
    setCsvKnnJobs([]);
    setCsvArtifacts([]);
    setCsvArtifactVerification(null);
    setCsvFile(null);
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
      setValidationReport(null);
      await refreshCurrent();
    } catch (ex) { setError(ease(ex)); }
  }, [accessToken, selectedDataset, selectedCategory, refreshCurrent]);

  const handleValidateDataset = useCallback(async () => {
    if (!selectedDataset) return;
    setIsValidating(true);
    setError('');
    try {
      setValidationReport(await validateDataset(accessToken, selectedDataset));
    } catch (ex) {
      setValidationReport(null);
      setError(ease(ex));
    } finally {
      setIsValidating(false);
    }
  }, [accessToken, selectedDataset]);

  const handleCsvPreview = useCallback(async (file: File | undefined) => {
    if (!file || !selectedDataset) return;
    setIsPreviewingCsv(true);
    setError('');
    try {
      setCsvFile(file);
      setCsvPreview(await previewCsv(accessToken, selectedDataset, file));
      setCsvPreparation(null);
      setCsvSnapshot(null);
      setCsvProcessedPreview(null);
      setCsvArtifact(null);
      setCsvArtifacts([]);
      setCsvArtifactVerification(null);
      setCsvTargetColumn('');
      setCsvFeatureColumns([]);
    } catch (ex) {
      setCsvPreview(null);
      setError(ease(ex));
    } finally {
      setIsPreviewingCsv(false);
    }
  }, [accessToken, selectedDataset]);

  const handlePrepareCsv = useCallback(async () => {
    if (!csvFile || !selectedDataset || !csvTargetColumn || csvFeatureColumns.length === 0) return;
    setIsPreparingCsv(true);
    setError('');
    try {
      setCsvPreparation(await prepareCsv(accessToken, selectedDataset, csvFile, csvTargetColumn, csvFeatureColumns, csvSplit));
    } catch (ex) {
      setCsvPreparation(null);
      setError(ease(ex));
    } finally {
      setIsPreparingCsv(false);
    }
  }, [accessToken, csvFile, csvFeatureColumns, csvSplit, csvTargetColumn, selectedDataset]);

  const handleCreateCsvSnapshot = useCallback(async () => {
    if (!csvFile || !selectedDataset || !csvTargetColumn || csvFeatureColumns.length === 0) return;
    setIsCreatingCsvSnapshot(true);
    setError('');
    setCsvProcessedPreview(null);
    setCsvArtifact(null);
    try {
      setCsvSnapshot(await createCsvPreparationSnapshot(accessToken, selectedDataset, csvFile, csvTargetColumn, csvFeatureColumns, csvSplit, csvPolicy));
    } catch (ex) {
      setCsvSnapshot(null);
      setError(ease(ex));
    } finally {
      setIsCreatingCsvSnapshot(false);
    }
  }, [accessToken, csvFile, csvFeatureColumns, csvPolicy, csvSplit, csvTargetColumn, selectedDataset]);

  const handlePreviewProcessedCsv = useCallback(async () => {
    if (!selectedDataset || !csvSnapshot) return;
    setIsPreviewingProcessedCsv(true);
    setError('');
    setCsvArtifactVerification(null);
    try {
      setCsvProcessedPreview(await previewCsvPreprocessing(accessToken, selectedDataset, csvSnapshot.preparationId));
    } catch (ex) {
      setCsvProcessedPreview(null);
      setError(ease(ex));
    } finally {
      setIsPreviewingProcessedCsv(false);
    }
  }, [accessToken, csvSnapshot, selectedDataset]);

  const handleCreateCsvArtifact = useCallback(async () => {
    if (!selectedDataset || !csvSnapshot) return;
    setIsCreatingCsvArtifact(true);
    setError('');
    setCsvArtifactVerification(null);
    try {
      setCsvArtifact(await createCsvProcessedArtifact(accessToken, selectedDataset, csvSnapshot.preparationId));
      setCsvArtifacts(await readCsvProcessedArtifacts(accessToken, selectedDataset, csvSnapshot.preparationId));
    } catch (ex) {
      setCsvArtifact(null);
      setError(ease(ex));
    } finally {
      setIsCreatingCsvArtifact(false);
    }
  }, [accessToken, csvSnapshot, selectedDataset]);

  const handleVerifyCsvArtifact = useCallback(async (artifactId: string) => {
    if (!selectedDataset || !csvSnapshot) return;
    setIsVerifyingCsvArtifact(true);
    setError('');
    try {
      setCsvArtifactVerification(await verifyCsvProcessedArtifact(accessToken, selectedDataset, csvSnapshot.preparationId, artifactId));
    } catch (ex) {
      setCsvArtifactVerification(null);
      setError(ease(ex));
    } finally {
      setIsVerifyingCsvArtifact(false);
    }
  }, [accessToken, csvSnapshot, selectedDataset]);

  const handleTrainCsvKnn = useCallback(async () => {
    if (!selectedDataset || !csvSnapshot || !csvArtifact || !csvArtifactVerification?.isValid) return;
    setIsTrainingCsvKnn(true);
    setError('');
    try {
      const job = await createCsvKnnTrainingJob(accessToken, selectedDataset, csvSnapshot.preparationId, csvArtifact.artifactId, csvKnnK);
      setCsvKnnJobs(await readCsvKnnTrainingJobs(accessToken, selectedDataset, csvSnapshot.preparationId, csvArtifact.artifactId));
      setCsvArtifactVerification(await verifyCsvProcessedArtifact(accessToken, selectedDataset, csvSnapshot.preparationId, csvArtifact.artifactId));
      if (!job) setError('KNN training returned no job result.');
    } catch (ex) {
      setError(ease(ex));
    } finally {
      setIsTrainingCsvKnn(false);
    }
  }, [accessToken, csvArtifact, csvArtifactVerification, csvKnnK, csvSnapshot, selectedDataset]);

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
      <DatasetBrowser
        datasets={datasets}
        datasetDetail={datasetDetail}
        selectedDataset={selectedDataset}
        selectedCategory={selectedCategory}
        isLoading={isLoading}
        onCreateDataset={handleCreateDataset}
        onSelectDataset={(name) => void selectDataset(name)}
        onSelectCategory={(datasetName, categoryName) => void selectCategory(datasetName, categoryName)}
        onRenameDataset={handleRenameDataset}
        onDeleteDataset={handleDeleteDataset}
        onExport={handleExport}
        onCreateCategory={handleCreateCategory}
        onRenameCategory={(categoryName) => void handleRenameCategoryAt(categoryName)}
        onDeleteCategory={(categoryName) => void handleDeleteCategory(categoryName)}
      />

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
            <button type="button" disabled={!selectedDataset || isValidating} onClick={() => void handleValidateDataset()}>
              {isValidating ? 'Validating…' : 'Validate dataset'}
            </button>
            <label className="dataset-toolbar__file-button">
              {isPreviewingCsv ? 'Reading CSV…' : 'Preview CSV'}
              <input type="file" accept=".csv,text/csv" hidden disabled={!selectedDataset || isPreviewingCsv} onChange={(event) => void handleCsvPreview(event.target.files?.[0])} />
            </label>
          </div>
        </div>

        {error && <div className="dataset-page__error">{error}</div>}
        {validationReport && (
          <section className={`dataset-validation ${validationReport.isValid ? 'dataset-validation--valid' : 'dataset-validation--invalid'}`} aria-live="polite">
            <div>
              <strong>{validationReport.isValid ? 'Dataset ready' : 'Dataset needs review'}</strong>
              <span>{validationReport.validFileCount}/{validationReport.fileCount} valid files · {validationReport.duplicateFileCount} duplicates</span>
            </div>
            {validationReport.issues.length > 0 && (
              <details>
                <summary>Review {validationReport.issues.length} issue{validationReport.issues.length === 1 ? '' : 's'}</summary>
                <ul>
                  {validationReport.issues.map((issue) => <li key={`${issue.categoryName}-${issue.filename}-${issue.code}`}><code>{issue.code}</code> {issue.categoryName}/{issue.filename}: {issue.message}</li>)}
                </ul>
              </details>
            )}
          </section>
        )}
        {csvPreview && (
          <section className="dataset-csv-preview" aria-live="polite">
            <div className="dataset-csv-preview__heading">
              <strong>{csvPreview.filename}</strong>
              <span>{csvPreview.rowCount} rows · {csvPreview.columns.length} columns · delimiter {csvPreview.delimiter === '\\t' ? 'tab' : csvPreview.delimiter}</span>
            </div>
            <div className="dataset-csv-preview__columns">
              {csvPreview.columns.map((column) => (
                <label key={column.name} className="dataset-csv-preview__columns-item">
                  <input
                    type="checkbox"
                    checked={csvFeatureColumns.includes(column.name)}
                    disabled={csvTargetColumn === column.name}
                    onChange={(event) => { setCsvFeatureColumns((current) => event.target.checked ? [...current, column.name] : current.filter((value) => value !== column.name)); setCsvPreparation(null); setCsvSnapshot(null); }}
                  />
                  <strong>{column.name}</strong>
                  <small>{column.dataType} · {column.missingCount} missing</small>
                </label>
              ))}
            </div>
            <div className="dataset-csv-preview__prepare">
              <label>Target column
                <select value={csvTargetColumn} onChange={(event) => { setCsvTargetColumn(event.target.value); setCsvFeatureColumns((current) => current.filter((value) => value !== event.target.value)); setCsvPreparation(null); setCsvSnapshot(null); }}>
                  <option value="">Select target</option>
                  {csvPreview.columns.map((column) => <option key={column.name} value={column.name}>{column.name}</option>)}
                </select>
              </label>
              <label>Train <input type="number" min="0.01" max="0.98" step="0.01" value={csvSplit.train} onChange={(event) => { setCsvSplit((current) => ({ ...current, train: Number(event.target.value) })); setCsvPreparation(null); setCsvSnapshot(null); }} /></label>
              <label>Validation <input type="number" min="0.01" max="0.98" step="0.01" value={csvSplit.validation} onChange={(event) => { setCsvSplit((current) => ({ ...current, validation: Number(event.target.value) })); setCsvPreparation(null); setCsvSnapshot(null); }} /></label>
              <label>Test <input type="number" min="0.01" max="0.98" step="0.01" value={csvSplit.test} onChange={(event) => { setCsvSplit((current) => ({ ...current, test: Number(event.target.value) })); setCsvPreparation(null); setCsvSnapshot(null); }} /></label>
              <label>Numeric missing
                <select value={csvPolicy.numeric_missing} onChange={(event) => { setCsvPolicy((current) => ({ ...current, numeric_missing: event.target.value })); setCsvPreparation(null); setCsvSnapshot(null); }}><option value="error">Reject</option><option value="mean">Mean</option><option value="median">Median</option></select>
              </label>
              <label>Categorical missing
                <select value={csvPolicy.categorical_missing} onChange={(event) => { setCsvPolicy((current) => ({ ...current, categorical_missing: event.target.value })); setCsvPreparation(null); setCsvSnapshot(null); }}><option value="error">Reject</option><option value="most-frequent">Most frequent</option><option value="constant">Constant</option></select>
              </label>
              <label>Scaling
                <select value={csvPolicy.scaling} onChange={(event) => { setCsvPolicy((current) => ({ ...current, scaling: event.target.value })); setCsvPreparation(null); setCsvSnapshot(null); }}><option value="none">None</option><option value="standard">Standard</option></select>
              </label>
              <label>Categories
                <select value={csvPolicy.categorical_encoding} onChange={(event) => { setCsvPolicy((current) => ({ ...current, categorical_encoding: event.target.value })); setCsvPreparation(null); setCsvSnapshot(null); }}><option value="none">None</option><option value="one-hot">One-hot</option></select>
              </label>
              <button type="button" disabled={!csvTargetColumn || csvFeatureColumns.length === 0 || isPreparingCsv} onClick={() => void handlePrepareCsv()}>{isPreparingCsv ? 'Preparing…' : 'Prepare split'}</button>
              <button type="button" disabled={!csvPreparation || isCreatingCsvSnapshot} onClick={() => void handleCreateCsvSnapshot()}>{isCreatingCsvSnapshot ? 'Saving…' : 'Save immutable snapshot'}</button>
            </div>
            {csvPreview.warnings.length > 0 && <p>{csvPreview.warnings.join(' ')}</p>}
          </section>
        )}
        {csvPreparation && (
          <section className="dataset-csv-preparation" aria-live="polite">
            <strong>Preparation ready</strong>
            <span>{csvPreparation.trainRows} train · {csvPreparation.validationRows} validation · {csvPreparation.testRows} test rows</span>
            <span>Target: {csvPreparation.targetColumn} · Features: {csvPreparation.featureColumns.join(', ')}</span>
            {csvPreparation.warnings.length > 0 && <p>{csvPreparation.warnings.join(' ')}</p>}
          </section>
        )}
        {csvSnapshot && (
          <section className="dataset-csv-snapshot" aria-live="polite">
            <strong>Immutable snapshot saved</strong>
            <span>{csvSnapshot.preparationId}</span>
            <small>Source SHA-256: {csvSnapshot.sourceSha256}</small>
            <button type="button" disabled={isPreviewingProcessedCsv} onClick={() => void handlePreviewProcessedCsv()}>{isPreviewingProcessedCsv ? 'Processing…' : 'Preview processed data'}</button>
            <button type="button" disabled={!csvProcessedPreview || isCreatingCsvArtifact} onClick={() => void handleCreateCsvArtifact()}>{isCreatingCsvArtifact ? 'Materializing…' : 'Save processed artifact'}</button>
          </section>
        )}
        {csvSnapshot && csvProcessedPreview && (
          <section className="dataset-csv-processed" aria-live="polite">
            <strong>Processed preview</strong>
            <span>{csvProcessedPreview.trainRows} train · {csvProcessedPreview.validationRows} validation · {csvProcessedPreview.testRows} test</span>
            <span>Columns: {csvProcessedPreview.processedColumns.join(', ')}</span>
            {csvProcessedPreview.warnings.map((warning) => <small key={warning}>{warning}</small>)}
          </section>
        )}
        {csvArtifact && (
          <section className="dataset-csv-artifact" aria-live="polite">
            <strong>Processed artifact saved</strong>
            <span>{csvArtifact.artifactId}</span>
            <small>Manifest SHA-256: {csvArtifact.manifestSha256}</small>
            <button type="button" disabled={isVerifyingCsvArtifact} onClick={() => void handleVerifyCsvArtifact(csvArtifact.artifactId)}>{isVerifyingCsvArtifact ? 'Verifying…' : 'Verify checksums'}</button>
            <label>K <input type="number" min="1" max="25" value={csvKnnK} onChange={(event) => setCsvKnnK(Number(event.target.value))} /></label>
            <button type="button" disabled={!csvArtifactVerification?.isValid || isTrainingCsvKnn} onClick={() => void handleTrainCsvKnn()}>{isTrainingCsvKnn ? 'Training…' : 'Train KNN'}</button>
          </section>
        )}
        {csvArtifacts.length > 0 && (
          <section className="dataset-csv-artifact-list" aria-live="polite">
            <strong>Saved artifacts ({csvArtifacts.length})</strong>
            {csvArtifacts.map((artifact) => <button key={artifact.artifactId} type="button" disabled={isVerifyingCsvArtifact} onClick={() => void handleVerifyCsvArtifact(artifact.artifactId)}>{artifact.artifactId}</button>)}
          </section>
        )}
        {csvArtifactVerification && (
          <section className={`dataset-csv-verification ${csvArtifactVerification.isValid ? 'dataset-csv-verification--valid' : 'dataset-csv-verification--invalid'}`} aria-live="polite">
            <strong>{csvArtifactVerification.isValid ? 'Artifact checksums verified' : 'Artifact integrity check failed'}</strong>
            {csvArtifactVerification.issues.map((issue) => <small key={issue}>{issue}</small>)}
          </section>
        )}
        {csvKnnJobs.length > 0 && (
          <section className="dataset-csv-jobs" aria-live="polite">
            <strong>KNN jobs ({csvKnnJobs.length})</strong>
            {csvKnnJobs.map((job) => <span key={job.jobId}>{job.jobId} · k={job.k} · validation {job.validationAccuracy ?? 'n/a'} · test {job.testAccuracy ?? 'n/a'}</span>)}
          </section>
        )}

        <DatasetImageGrid
          accessToken={accessToken}
          datasetName={selectedDataset}
          categoryName={selectedCategory}
          getImageUrl={getImageUrl}
          images={images}
          isLoading={isDetailLoading}
          onSelectImage={setViewerImage}
          onRenameImage={(filename) => void handleRenameImage(filename)}
          onDeleteImage={(filename) => void handleDeleteImage(filename)}
        />

        <footer className="dataset-status">
          <span>
            {datasets.length} dataset{datasets.length === 1 ? '' : 's'} · {totalImagesCount} images · {formatBytes(totalSize)} total
          </span>
        </footer>
      </section>

      {viewerImage && selectedDataset && selectedCategory && (
        <DatasetImageViewer
          accessToken={accessToken}
          image={viewerImage}
          imageIndex={viewerIndex}
          imageCount={images.length}
          imageUrl={currentThumbUrl}
          formatBytes={formatBytes}
          onClose={() => setViewerImage(null)}
          onPrevious={showPrev}
          onNext={showNext}
          onDelete={() => void handleDeleteImage(viewerImage.filename)}
        />
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




