import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import { DatabasePage } from './DatabasePage';

vi.mock('../services/inspection-service', () => ({
  readInspectionMetrics: vi.fn(),
  readInspections: vi.fn(),
  submitReview: vi.fn(),
}));

describe('DatabasePage views', () => {
  it('keeps inspection data and offers PostgreSQL schema view', () => {
    const markup = renderToStaticMarkup(<DatabasePage accessToken="token" />);

    expect(markup).toContain('Inspection data');
    expect(markup).toContain('PostgreSQL');
  });
});