import { useCallback, useEffect, useMemo, useState } from 'react';
import { PostgreSQLSchemaPanel } from '../components/database/PostgreSQLSchemaPanel';
import { StatusBadge } from '../components/StatusBadge';
import { readDatabaseSchema } from '../services/database-schema-service';
import { readInspectionMetrics, readInspections, submitReview } from '../services/inspection-service';
import type { DatabaseSchema } from '../types/database-schema';
import type { InspectionFilters, InspectionListItem, InspectionListResponse, InspectionMetrics } from '../types/inspection';

const EMPTY_METRICS: InspectionMetrics = {
  totalInspections: 0, passCount: 0, failCount: 0, reviewCount: 0,
  firstPassYield: 0, totalDefects: 0, pendingReview: 0,
};
const PAGE_SIZE = 25;

export function DatabasePage({ accessToken }: { accessToken: string }) {
  const [activeDatabaseView, setActiveDatabaseView] = useState<'inspections' | 'postgresql'>('inspections');
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [resultFilter, setResultFilter] = useState('');
  const [page, setPage] = useState(1);
  const [metrics, setMetrics] = useState<InspectionMetrics>(EMPTY_METRICS);
  const [listResponse, setListResponse] = useState<InspectionListResponse | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<InspectionListItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [databaseSchema, setDatabaseSchema] = useState<DatabaseSchema | null>(null);
  const [isLoadingSchema, setIsLoadingSchema] = useState(false);
  const [schemaError, setSchemaError] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => { setDebouncedQuery(query.trim()); setPage(1); }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const filters: InspectionFilters = useMemo(() => ({
    page, pageSize: PAGE_SIZE,
    result: resultFilter || undefined,
    search: debouncedQuery || undefined,
  }), [page, resultFilter, debouncedQuery]);

  const loadData = useCallback(async () => {
    setError('');
    setIsLoading(true);
    try {
      const [m, l] = await Promise.all([
        readInspectionMetrics(accessToken),
        readInspections(accessToken, filters),
      ]);
      setMetrics(m);
      setListResponse(l);
      if (l.items.length > 0 && !selectedRecord) setSelectedRecord(l.items[0]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load data.');
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, filters, selectedRecord]);

  useEffect(() => { void loadData(); }, [loadData]);

  const loadDatabaseSchema = useCallback(async () => {
    setSchemaError('');
    setIsLoadingSchema(true);
    try {
      setDatabaseSchema(await readDatabaseSchema(accessToken));
    } catch (schemaFailure) {
      setSchemaError(schemaFailure instanceof Error ? schemaFailure.message : 'Could not load PostgreSQL schema.');
    } finally {
      setIsLoadingSchema(false);
    }
  }, [accessToken]);

  useEffect(() => {
    if (activeDatabaseView === 'postgresql' && databaseSchema === null && !isLoadingSchema && !schemaError) {
      void loadDatabaseSchema();
    }
  }, [activeDatabaseView, databaseSchema, isLoadingSchema, schemaError, loadDatabaseSchema]);

  const items = listResponse?.items ?? [];
  const totalPages = listResponse?.totalPages ?? 1;
  const total = listResponse?.total ?? 0;

  const handleReview = async (id: number, decision: 'PASS' | 'FAIL') => {
    try { await submitReview(accessToken, id, decision); void loadData(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Review failed.'); }
  };

  const exportRecords = () => {
    const header = 'Board ID,Recipe,Result,Defects,Score,Inspected At,Lot';
    const rows = items.map((r) =>
      [r.boardSerial, r.recipeName, r.result, r.defectCount, r.score ?? '', r.inspectedAt, r.lot]
        .map((v) => `"${String(v).replace(/"/g, '""')}"`).join(',')
    );
    const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'aoi-records.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  const fmt = (iso: string) => { try { return new Date(iso).toLocaleString(); } catch { return iso; } };

  const md = [
    { value: metrics.totalInspections.toLocaleString(), label: 'PCB records', note: `${metrics.pendingReview} pending review` },
    { value: `${metrics.firstPassYield}%`, label: 'First-pass yield', note: `${metrics.passCount} passed` },
    { value: String(metrics.failCount + metrics.reviewCount), label: 'Flagged boards', note: `${metrics.pendingReview} require review` },
    { value: metrics.totalDefects.toLocaleString(), label: 'Total defects', note: `${metrics.failCount} failed boards` },
  ];

  const sr = selectedRecord;

  return (
    <div className="database-page">
      <DatabaseHeader
        activeView={activeDatabaseView}
        onViewChange={setActiveDatabaseView}
        query={query}
        setQuery={setQuery}
        resultFilter={resultFilter}
        setResultFilter={setResultFilter}
        setPage={setPage}
      />
      {activeDatabaseView === 'inspections' ? (
        <>
          {error && <p className="studio-message studio-message--error">{error}</p>}
          <section className="database-metrics" aria-label="Database metrics">
            {md.map((m) => (<article key={m.label}><strong>{m.value}</strong><span>{m.label}</span><small>{m.note}</small></article>))}
          </section>
          <section className="database-layout">
            <RecordsPanel items={items} isLoading={isLoading} selectedId={sr?.id ?? null} total={total} page={page} totalPages={totalPages} debouncedQuery={debouncedQuery} onSelect={setSelectedRecord} onExport={exportRecords} onPageChange={setPage} fmt={fmt} />
            <EvidencePanel record={sr} onReview={handleReview} fmt={fmt} />
          </section>
        </>
      ) : (
        <PostgreSQLSchemaPanel schema={databaseSchema} isLoading={isLoadingSchema} error={schemaError} onRefresh={() => void loadDatabaseSchema()} />
      )}
    </div>
  );
}


function DatabaseHeader({ activeView, onViewChange, query, setQuery, resultFilter, setResultFilter, setPage }: any) {
  return (
    <header className="workspace-title-row database-header">
      <div>
        <span className="overline">Database</span>
        <h1>{activeView === 'inspections' ? 'Board history & evidence' : 'PostgreSQL schema'}</h1>
        <p>{activeView === 'inspections' ? 'Review inspection results, defect records, and captured evidence.' : 'Explore read-only tables, columns, indexes, constraints, and foreign keys.'}</p>
      </div>
      <div className="database-header__actions">
        <div className="database-view-switch" aria-label="Database view">
          <button type="button" className={activeView === 'inspections' ? 'is-active' : ''} aria-pressed={activeView === 'inspections'} onClick={() => onViewChange('inspections')}>Inspection data</button>
          <button type="button" className={activeView === 'postgresql' ? 'is-active' : ''} aria-pressed={activeView === 'postgresql'} onClick={() => onViewChange('postgresql')}>PostgreSQL</button>
        </div>
        {activeView === 'inspections' && (
          <div className="database-header__filters">
            <select aria-label="Filter inspection results" value={resultFilter} onChange={(e) => { setResultFilter(e.target.value); setPage(1); }}>
              <option value="">All results</option>
              <option value="PASS">Pass</option>
              <option value="FAIL">Fail</option>
              <option value="REVIEW">Review</option>
            </select>
            <label className="database-search">
              <span className="sr-only">Search inspection records</span>
              <span aria-hidden="true">⌕</span>
              <input value={query} placeholder="Search serial, lot, or recipe" onChange={(e) => setQuery(e.target.value)} />
            </label>
          </div>
        )}
      </div>
    </header>
  );
}

function RecordsPanel({ items, isLoading, selectedId, total, page, totalPages, debouncedQuery, onSelect, onExport, onPageChange, fmt }: any) {
  return (
    <div className="records-panel">
      <header className="section-heading">
        <div><span className="overline">Records</span><h2>Recent inspections</h2></div>
        <button className="studio-secondary-button" type="button" onClick={onExport} disabled={items.length === 0}>Export CSV</button>
      </header>
      <div className="records-table-wrap">
        {isLoading ? (
          <p style={{ padding: '24px', textAlign: 'center', color: 'var(--studio-muted)' }}>Loading inspection records…</p>
        ) : (
          <table className="records-table">
            <thead><tr><th>Board ID</th><th>Recipe</th><th>Result</th><th>Defects</th><th>Inspected</th></tr></thead>
            <tbody>
              {items.map((r: any) => (
                <tr key={r.id} className={selectedId === r.id ? 'records-table__selected' : ''} onClick={() => onSelect(r)}>
                  <td><button type="button" onClick={() => onSelect(r)}>{r.boardSerial}</button></td>
                  <td>{r.recipeName}</td>
                  <td><StatusBadge status={r.result === 'PASS' ? 'success' : r.result === 'FAIL' ? 'error' : 'warning'} label={r.result} /></td>
                  <td>{r.defectCount}</td>
                  <td>{fmt(r.inspectedAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {!isLoading && items.length === 0 && (
          <p className="empty-state">{debouncedQuery ? `No inspection records match "${debouncedQuery}".` : 'No inspection records found.'}</p>
        )}
      </div>
      <footer className="records-panel__footer">
        <span>Showing {items.length} of {total.toLocaleString()} records</span>
        <span style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          <button type="button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>← Prev</button>
          <span>{page} / {totalPages}</span>
          <button type="button" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Next →</button>
        </span>
      </footer>
    </div>
  );
}

function EvidencePanel({ record, onReview, fmt }: any) {
  if (!record) {
    return (
      <aside className="evidence-panel">
        <div style={{ padding: '24px', textAlign: 'center', color: 'var(--studio-muted)' }}>Select an inspection record.</div>
      </aside>
    );
  }

  return (
    <aside className="evidence-panel">
      <div className="panel-heading"><span>Selected evidence</span><span>{record.boardSerial}</span></div>
      <div className="evidence-preview" role="img" aria-label={`Captured PCB evidence for ${record.boardSerial}`}>
        <span className="evidence-board" />
        {record.defectCount > 0 && <span className="evidence-defect">Defect 01</span>}
      </div>
      <StatusBadge
        status={record.result === 'PASS' ? 'success' : record.result === 'FAIL' ? 'error' : 'warning'}
        label={record.result === 'REVIEW' ? `Review required · ${record.defectCount} defects` : record.result}
      />
      <dl className="property-list">
        <div><dt>Recipe</dt><dd>{record.recipeName}</dd></div>
        <div><dt>Lot</dt><dd>{record.lot || '—'}</dd></div>
        <div><dt>Score</dt><dd>{record.score != null ? record.score.toFixed(2) : '—'}</dd></div>
        <div><dt>Cycle time</dt><dd>{record.cycleTimeMs != null ? `${record.cycleTimeMs} ms` : '—'}</dd></div>
        <div><dt>Operator</dt><dd>{record.operatorName}</dd></div>
        <div><dt>Inspected</dt><dd>{fmt(record.inspectedAt)}</dd></div>
        {record.reviewDecision && (<div><dt>Review</dt><dd>{record.reviewDecision}</dd></div>)}
      </dl>
      {record.result === 'REVIEW' && !record.reviewDecision && (
        <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
          <button className="studio-primary-button" type="button" onClick={() => onReview(record.id, 'PASS')}>Accept (PASS)</button>
          <button className="studio-secondary-button" type="button" onClick={() => onReview(record.id, 'FAIL')}>Reject (FAIL)</button>
        </div>
      )}
    </aside>
  );
}