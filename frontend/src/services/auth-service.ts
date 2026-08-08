import type { AuthSession, LoginRequest } from '../types/auth';
import { apiRequest } from './api-client';

export function signIn(credentials: LoginRequest): Promise<AuthSession> {
  return apiRequest<AuthSession>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
}

export function requestPasswordReset(email: string): Promise<{ message: string }> {
  return apiRequest<{ message: string }>('/api/auth/password-reset', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}