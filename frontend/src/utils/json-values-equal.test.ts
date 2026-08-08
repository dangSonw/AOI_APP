import { describe, expect, it } from 'vitest';
import { jsonValuesEqual } from './json-values-equal';

describe('jsonValuesEqual', () => {
  it('treats objects with equal values and different key order as equal', () => {
    const desired = {
      cameraId: 'top-camera',
      analogGain: 1,
      sensorMode: '3280x2464',
      exposureMicroseconds: 8000,
    };
    const observed = {
      cameraId: 'top-camera',
      sensorMode: '3280x2464',
      exposureMicroseconds: 8000,
      analogGain: 1.0,
    };

    expect(jsonValuesEqual(desired, observed)).toBe(true);
  });

  it('rejects nested value differences', () => {
    expect(jsonValuesEqual({ motion: { settleMilliseconds: 100 } }, { motion: { settleMilliseconds: 101 } })).toBe(false);
  });
});
