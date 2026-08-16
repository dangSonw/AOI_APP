import { useMemo, useState } from 'react';
import type { AlgorithmDefinition } from '../../types/workflow';
import { filterCatalog } from '../../utils/workflow-graph';
import { RuntimeUseBadge } from '../RuntimeUseBadge';


export const ALGORITHM_DRAG_TYPE = 'application/x-aoi-algorithm';

interface AlgorithmCatalogProps {
  catalog: AlgorithmDefinition[];
  onAdd: (definition: AlgorithmDefinition) => void;
  onOpenDocumentation: (definition: AlgorithmDefinition) => void;
  onRetry: () => void;
}

export function AlgorithmCatalog({ catalog, onAdd, onOpenDocumentation, onRetry }: AlgorithmCatalogProps) {
  const [query, setQuery] = useState('');
  const filteredCatalog = useMemo(() => filterCatalog(catalog, query), [catalog, query]);
  const categories = useMemo(() => {
    const grouped = new Map<string, AlgorithmDefinition[]>();
    for (const definition of filteredCatalog) {
      grouped.set(definition.category, [...(grouped.get(definition.category) ?? []), definition]);
    }
    return [...grouped.entries()];
  }, [filteredCatalog]);

  return (
    <aside className="workflow-catalog" aria-label="Algorithm catalog">
      <header className="workflow-region-heading">
        <div><span className="overline">Core catalog</span><strong>Algorithms</strong></div>
        <span>{filteredCatalog.length}/{catalog.length}</span>
      </header>
      <label className="workflow-search">
        <span className="sr-only">Search algorithms</span>
        <input
          type="search"
          value={query}
          placeholder="Search methods, groups, IDs"
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      {catalog.length === 0 ? (
        <div className="workflow-empty">
          <strong>No algorithm definitions</strong>
          <p>The core catalog could not be loaded.</p>
          <button type="button" className="secondary-button" onClick={onRetry}>Retry catalog</button>
        </div>
      ) : categories.length === 0 ? (
        <div className="workflow-empty"><strong>No matches</strong><p>Try a method name, group, or algorithm ID.</p></div>
      ) : (
        <div className="workflow-catalog__groups">
          {categories.map(([category, definitions]) => (
            <section className="workflow-catalog__group" key={category}>
              <h3>{category}<span>{definitions.length}</span></h3>
              <div className="workflow-catalog__items">
                {definitions.map((definition) => (
                  <article
                    className="algorithm-card"
                    draggable
                    key={definition.id}
                    onDragStart={(event) => {
                      event.dataTransfer.effectAllowed = 'copy';
                      event.dataTransfer.setData(ALGORITHM_DRAG_TYPE, definition.id);
                    }}
                  >
                    <button
                      type="button"
                      className="algorithm-card__documentation"
                      aria-label={`Open documentation for ${definition.name}`}
                      onClick={() => onOpenDocumentation(definition)}
                    >
                      <span className="algorithm-card__title">
                        <strong>{definition.name}</strong>
                        <code>{definition.id}</code>
                      </span>
                      <span className="algorithm-card__description">{definition.description}</span>
                      <span className="algorithm-card__hint">View README</span>
                    </button>
                    <footer>
                      <RuntimeUseBadge use={definition.use} />
                      <button type="button" onClick={() => onAdd(definition)} aria-label={`Add ${definition.name}`}>Add</button>
                    </footer>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </aside>
  );
}