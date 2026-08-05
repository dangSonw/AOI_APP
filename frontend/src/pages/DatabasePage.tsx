import { useMemo, useState } from 'react';
import { StatusBadge } from '../components/StatusBadge';
import type { InspectionRecord } from '../types/workspace';
import { filterInspectionRecords, INSPECTION_RECORDS } from '../utils/inspection-records';

const DATABASE_METRICS = [
  { value: '12,481', label: 'PCB records', note: '+5.2% this week' },
  { value: '99.1%', label: 'First-pass yield', note: '+0.4% from last week' },
  { value: '286', label: 'Flagged boards', note: '18 require review' },
  { value: '4.8 TB', label: 'Image archive', note: '82% storage utilised' },
];

export function DatabasePage() {
  const [query, setQuery] = useState('');
  const [selectedRecord, setSelectedRecord] = useState<InspectionRecord>(INSPECTION_RECORDS[1]);
  const filteredRecords = useMemo(() => filterInspectionRecords(INSPECTION_RECORDS, query), [query]);

  const exportRecords = () => {
    const header = 'Board ID,Recipe,Result,Defects,Captured,Lot';
    const rows = filteredRecords.map((record) => (
      [record.boardId, record.recipe, record.result, record.defects, record.capturedAt, record.lot]
        .map((value) => `"${String(value).replace(/"/g, '""')}"`)
        .join(',')
    ));
    const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'aoi-inspection-records.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="database-page">
      <header className="workspace-title-row database-header">
        <div>
          <span className="overline">Inspection database</span>
          <h1>Board history & evidence</h1>
          <p>Review inspection results, defect records, and captured evidence.</p>
        </div>
        <label className="database-search">
          <span className="sr-only">Search inspection records</span>
          <span aria-hidden="true">⌕</span>
          <input value={query} placeholder="Search serial, lot, recipe, or result" onChange={(event) => setQuery(event.target.value)} />
        </label>
      </header>

      <section className="database-metrics" aria-label="Database metrics">
        {DATABASE_METRICS.map((metric) => (
          <article key={metric.label}>
            <strong>{metric.value}</strong>
            <span>{metric.label}</span>
            <small>{metric.note}</small>
          </article>
        ))}
      </section>

      <section className="database-layout">
        <div className="records-panel">
          <header className="section-heading">
            <div><span className="overline">Records</span><h2>Recent inspections</h2></div>
            <button className="studio-secondary-button" type="button" onClick={exportRecords}>Export CSV</button>
          </header>
          <div className="records-table-wrap">
            <table className="records-table">
              <thead><tr><th>Board ID</th><th>Recipe</th><th>Result</th><th>Defects</th><th>Captured</th></tr></thead>
              <tbody>
                {filteredRecords.map((record) => (
                  <tr
                    key={record.boardId}
                    className={record.boardId === selectedRecord.boardId ? 'records-table__selected' : ''}
                    onClick={() => setSelectedRecord(record)}
                  >
                    <td><button type="button" onClick={() => setSelectedRecord(record)}>{record.boardId}</button></td>
                    <td>{record.recipe}</td>
                    <td><StatusBadge status={record.result === 'PASS' ? 'success' : record.result === 'FAIL' ? 'error' : 'warning'} label={record.result} /></td>
                    <td>{record.defects}</td>
                    <td>{record.capturedAt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredRecords.length === 0 && <p className="empty-state">No inspection records match “{query}”.</p>}
          </div>
          <footer className="records-panel__footer">Showing {filteredRecords.length} of 12,481 records <span>1&nbsp;&nbsp;2&nbsp;&nbsp;3&nbsp;&nbsp; Next →</span></footer>
        </div>

        <aside className="evidence-panel">
          <div className="panel-heading"><span>Selected evidence</span><span>{selectedRecord.boardId}</span></div>
          <div className="evidence-preview" role="img" aria-label={`Captured PCB evidence for ${selectedRecord.boardId}`}>
            <span className="evidence-board" />
            {selectedRecord.defects > 0 && <span className="evidence-defect">Defect 01</span>}
          </div>
          <StatusBadge
            status={selectedRecord.result === 'PASS' ? 'success' : selectedRecord.result === 'FAIL' ? 'error' : 'warning'}
            label={selectedRecord.result === 'REVIEW' ? `Review required · ${selectedRecord.defects} defects` : selectedRecord.result}
          />
          <dl className="property-list">
            <div><dt>Recipe</dt><dd>{selectedRecord.recipe}</dd></div>
            <div><dt>Lot</dt><dd>{selectedRecord.lot}</dd></div>
            <div><dt>Camera</dt><dd>Top camera · 12 MP</dd></div>
            <div><dt>Illumination</dt><dd>4× synchronized</dd></div>
            <div><dt>Captured</dt><dd>{selectedRecord.capturedAt}</dd></div>
          </dl>
          <button className="studio-primary-button" type="button" disabled title="Defect review is not available in this milestone">Open defect review</button>
        </aside>
      </section>
    </div>
  );
}