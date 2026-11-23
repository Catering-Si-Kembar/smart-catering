import axios, { type AxiosInstance } from 'axios';

export function resolveServerApiBaseUrl(
  env: Record<string, string | undefined> = process.env,
): string {
  if (typeof window !== 'undefined') {
    throw new Error('resolveServerApiBaseUrl must only be called on the server');
  }

  const rawUrl = env.API_BASE_URL?.trim();
  if (rawUrl) {
    return rawUrl.replace(/\/+$/, '');
  }

  return 'http://127.0.0.1:3001';
}

export function createServerApiClient(requestId?: string | null): AxiosInstance {
  const headers: Record<string, string> = {
    Accept: 'application/json',
  };

  const trimmedRequestId = requestId?.trim();
  if (trimmedRequestId) {
    headers['X-Request-Id'] = trimmedRequestId;
  }

  return axios.create({
    baseURL: resolveServerApiBaseUrl(),
    timeout: 10_000,
    headers,
  });
}
