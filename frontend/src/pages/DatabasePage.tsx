import { useCallback, useEffect, useMemo, useState } from 'react';
import { StatusBadge } from '../components/StatusBadge';
import { readInspectionMetrics, readInspections, submitReview } from '../services/inspection-service';
import type { InspectionFilters, InspectionListItem, InspectionListResponse, InspectionMetrics } from '../types/inspection';

const EMPTY_METRICS: InspectionMetrics = {
  totalInspections: 0, passCount: 0, failCount: 0, reviewCount: 0,
  firstPassYield: 0, totalDefects: 0, pendingReview: 0,
};
const PAGE_SIZE = 25;

export function DatabasePage({ accessToken }: { accessToken: string }) {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [resultFilter, setResultFilter] = useState('');
  const [page, setPage] = useState(1);
  const [metrics, setMetrics] = useState<InspectionMetrics>(EMPTY_METRICS);
  const [listResponse, setListResponse] = useState<InspectionListResponse | null>(null);
  const [selectedRecord, setSelectedRecord] = useState<InspectionListItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

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
        .map((v) => \
