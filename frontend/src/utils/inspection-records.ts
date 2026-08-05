import type { InspectionRecord } from '../types/workspace';

export const INSPECTION_RECORDS: InspectionRecord[] = [
  { boardId: 'PCB-24-08192', recipe: 'Rev C · Mainboard', result: 'PASS', defects: 0, capturedAt: '14:32:18', lot: 'MFG-2408-C' },
  { boardId: 'PCB-24-08191', recipe: 'Rev C · Mainboard', result: 'REVIEW', defects: 2, capturedAt: '14:31:42', lot: 'MFG-2408-C' },
  { boardId: 'PCB-24-08190', recipe: 'Rev B · Power', result: 'FAIL', defects: 5, capturedAt: '14:29:07', lot: 'MFG-2408-B' },
  { boardId: 'PCB-24-08189', recipe: 'Rev C · Mainboard', result: 'PASS', defects: 0, capturedAt: '14:27:55', lot: 'MFG-2408-C' },
  { boardId: 'PCB-24-08188', recipe: 'Rev A · Sensor', result: 'PASS', defects: 0, capturedAt: '14:26:11', lot: 'MFG-2408-A' },
  { boardId: 'PCB-24-08187', recipe: 'Rev B · Power', result: 'REVIEW', defects: 1, capturedAt: '14:24:39', lot: 'MFG-2408-B' },
];

export function filterInspectionRecords(records: InspectionRecord[], query: string): InspectionRecord[] {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return records;
  }

  return records.filter((record) => (
    record.boardId.toLowerCase().includes(normalizedQuery)
    || record.recipe.toLowerCase().includes(normalizedQuery)
    || record.result.toLowerCase().includes(normalizedQuery)
    || record.lot.toLowerCase().includes(normalizedQuery)
  ));
}