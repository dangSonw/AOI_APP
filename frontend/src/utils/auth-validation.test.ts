import { describe, expect, it } from 'vitest';
import {
  hasValidationErrors,
  validateEmail,
  validateLogin,
  validateRegistration,
} from './auth-validation';

describe('authentication validation', () => {
  it('accepts a valid work email', () => {
    expect(validateEmail('operator@aoi.local')).toBeUndefined();
  });

  it('reports missing login credentials', () => {
    expect(hasValidationErrors(validateLogin('', ''))).toBe(true);
  });

  it('requires matching passwords during registration', () => {
    const errors = validateRegistration(
      'operator@aoi.local',
      'AOI Operator',
      'inspection-123',
      'different-123',
    );

    expect(errors.confirmPassword).toBe('Passwords do not match.');
  });
});