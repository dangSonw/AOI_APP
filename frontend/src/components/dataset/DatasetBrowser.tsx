import type { DatasetDetail, DatasetSummary } from '../../types/dataset';

interface DatasetBrowserProps {
  datasets: DatasetSummary[];
  datasetDetail: DatasetDetail | null;
  selectedDataset: string | null;
  selectedCategory: string | null;
  isLoading: boolean;
  onCreateDataset: () => void;
  onSelectDataset: (name: string) => void;
  onSelectCategory: (datasetName: string, categoryName: string) => void;
  onRenameDataset: () => void;
  onDeleteDataset: () => void;
  onExport: () => void;
  onCreateCategory: () => void;
  onRenameCategory: (categoryName: string) => void;
  onDeleteCategory: (categoryName: string) => void;
}

export function DatasetBrowser({
  datasets,
  datasetDetail,
  selectedDataset,
  selectedCategory,
  isLoading,
  onCreateDataset,
  onSelectDataset,
  onSelectCategory,
  onRenameDataset,
  onDeleteDataset,
  onExport,
  onCreateCategory,
  onRenameCategory,
  onDeleteCategory,
}: DatasetBrowserProps) {
  return (
    <aside className="dataset-browser" aria-label="Dataset browser">
      <div className="panel-heading"><span>Datasets</span></div>
      <button type="button" className="studio-primary-button dataset-browser__new" onClick={onCreateDataset}>
        + New dataset
      </button>
      {isLoading ? (
        <p className="dataset-browser__empty" role="status">Loading…</p>
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
                  aria-current={isActive ? 'true' : undefined}
                  onClick={() => onSelectDataset(dataset.name)}
                >
                  <span className="dataset-browser__label">{dataset.name}</span>
                  <span className="dataset-browser__meta">{dataset.totalImages} img</span>
                </button>
                {isActive && (
                  <div className="dataset-browser__actions">
                    <button type="button" onClick={onRenameDataset}>Rename</button>
                    <button type="button" onClick={onDeleteDataset}>Delete</button>
                    <button type="button" onClick={onExport}>Export</button>
                  </div>
                )}
                {isActive && (
                  <ul className="dataset-browser__categories">
                    {(detail?.categories ?? []).map((category) => {
                      const isCategoryActive = category.name === selectedCategory;
                      return (
                        <li key={category.name}>
                          <button
                            type="button"
                            className={`dataset-browser__category ${isCategoryActive ? 'dataset-browser__category--active' : ''}`}
                            aria-current={isCategoryActive ? 'true' : undefined}
                            onClick={() => onSelectCategory(dataset.name, category.name)}
                          >
                            {category.name} ({category.imageCount})
                          </button>
                          {isCategoryActive && (
                            <div className="dataset-browser__actions">
                              <button type="button" onClick={() => onRenameCategory(category.name)}>Rename</button>
                              <button type="button" onClick={() => onDeleteCategory(category.name)}>Delete</button>
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
                {isActive && (
                  <button type="button" className="dataset-browser__add-category" onClick={onCreateCategory}>
                    + Category
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </aside>
  );
}