const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');

interface ApiErrorBody {
  detail?: unknown;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  accessToken?: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');

  if (options.body) {
    headers.set('Content-Type', 'application/json');
  }
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError('The AOI service is unavailable. Check the backend connection.', 0);
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({})) as ApiErrorBody;
    const detail = errorBody.detail;
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail) && typeof detail[0]?.message === 'string'
        ? detail[0].message
        : 'The request could not be completed.';
    throw new ApiError(message, response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export async function apiBlobRequest(path: string, accessToken: string): Promise<Blob> {
  const headers = new Headers({ Authorization: `Bearer ${accessToken}` });
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { headers, cache: 'no-store' });
  } catch {
    throw new ApiError('The AOI service is unavailable. Check the backend connection.', 0);
  }
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({})) as ApiErrorBody;
    throw new ApiError(
      typeof errorBody.detail === 'string' ? errorBody.detail : 'The request could not be completed.',
      response.status,
      errorBody.detail,
    );
  }
  return response.blob();
}