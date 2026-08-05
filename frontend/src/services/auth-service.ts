import type { AuthSession, LoginRequest, RegisterRequest } from '../types/auth';
import { apiRequest } from './api-client';

export function signIn(credentials: LoginRequest): Promise<AuthSession> {
  return apiRequest<AuthSession>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
}

export function createAccount(account: RegisterRequest): Promise<AuthSession> {
  return apiRequest<AuthSession>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(account),
  });
}

export function requestPasswordReset(email: string): Promise<{ message: string }> {
  return apiRequest<{ message: string }>('/api/auth/password-reset', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}