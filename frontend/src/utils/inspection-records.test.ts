import { describe, expect, it } from 'vitest';
import { filterInspectionRecords, INSPECTION_RECORDS } from './inspection-records';

describe('inspection record filtering', () => {
  it('returns all records for an empty query', () => {
    expect(filterInspectionRecords(INSPECTION_RECORDS, '')).toHaveLength(INSPECTION_RECORDS.length);
  });

  it('matches board, recipe, result, and lot values without case sensitivity', () => {
    expect(filterInspectionRecords(INSPECTION_RECORDS, '08191')).toHaveLength(1);
    expect(filterInspectionRecords(INSPECTION_RECORDS, 'sensor')).toHaveLength(1);
    expect(filterInspectionRecords(INSPECTION_RECORDS, 'fail')).toHaveLength(1);
    expect(filterInspectionRecords(INSPECTION_RECORDS, 'mfg-2408-b')).toHaveLength(2);
  });
});