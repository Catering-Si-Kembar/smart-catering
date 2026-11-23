import axios, { type AxiosInstance } from 'axios';
import type { ProblemDetails } from '@smart-catering/types';

export const apiClient: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10_000,
  headers: {
    Accept: 'application/json',
  },
});

export function normalizeApiError(error: unknown, fallbackInstance = '/api'): ProblemDetails {
  if (axios.isAxiosError(error) && error.response?.data) {
    const data = error.response.data as Partial<ProblemDetails>;
    if (typeof data === 'object' && data !== null && typeof data.title === 'string') {
      return {
        type: 'about:blank',
        title: data.title,
        status: typeof data.status === 'number' ? data.status : (error.response.status ?? 500),
        detail: typeof data.detail === 'string' ? data.detail : error.message,
        instance: typeof data.instance === 'string' ? data.instance : fallbackInstance,
        requestId:
          typeof data.requestId === 'string'
            ? data.requestId
            : String(error.response.headers?.['x-request-id'] || 'unknown'),
        ...(Array.isArray(data.errors) ? { errors: data.errors } : {}),
      };
    }
  }

  const message = error instanceof Error ? error.message : 'An unexpected error occurred';
  return {
    type: 'about:blank',
    title: 'Internal Server Error',
    status: axios.isAxiosError(error) && error.response ? error.response.status : 500,
    detail: message,
    instance: fallbackInstance,
    requestId:
      axios.isAxiosError(error) && error.response?.headers?.['x-request-id']
        ? String(error.response.headers['x-request-id'])
        : 'unknown',
  };
}
