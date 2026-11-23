import { afterEach, describe, expect, it } from 'vitest';
import { AxiosError, AxiosHeaders } from 'axios';
import { apiClient, normalizeApiError } from './client';
import { createServerApiClient, resolveServerApiBaseUrl } from './server';

describe('client api utilities', () => {
  it('configures apiClient with /api baseURL and JSON accept header', () => {
    expect(apiClient.defaults.baseURL).toBe('/api');
    expect(apiClient.defaults.timeout).toBe(10_000);
    expect(apiClient.defaults.headers.Accept).toBe('application/json');
  });

  describe('normalizeApiError', () => {
    it('extracts ProblemDetails from AxiosError response', () => {
      const error = new AxiosError('Bad Request', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 400,
        statusText: 'Bad Request',
        headers: { 'x-request-id': 'req-999' },
        config: { headers: new AxiosHeaders() },
        data: {
          type: 'about:blank',
          title: 'Validation Error',
          status: 400,
          detail: 'Invalid input',
          instance: '/api/v1/resource',
          requestId: 'req-123',
          errors: [
            { path: 'name', code: 'invalid_value' as const, message: 'Invalid value' as const },
          ],
        },
      });

      const normalized = normalizeApiError(error);
      expect(normalized).toEqual({
        type: 'about:blank',
        title: 'Validation Error',
        status: 400,
        detail: 'Invalid input',
        instance: '/api/v1/resource',
        requestId: 'req-123',
        errors: [{ path: 'name', code: 'invalid_value', message: 'Invalid value' }],
      });
    });

    it('handles AxiosError with non-ProblemDetails object data', () => {
      const error = new AxiosError('Not Found', 'ERR_NOT_FOUND', undefined, undefined, {
        status: 404,
        statusText: 'Not Found',
        headers: { 'x-request-id': 'header-req' },
        config: { headers: new AxiosHeaders() },
        data: 'Not found string',
      });

      const normalized = normalizeApiError(error, '/fallback');
      expect(normalized.title).toBe('Internal Server Error');
      expect(normalized.status).toBe(404);
      expect(normalized.detail).toBe('Not Found');
      expect(normalized.instance).toBe('/fallback');
      expect(normalized.requestId).toBe('header-req');
    });

    it('falls back to header requestId when data.requestId is missing in ProblemDetails', () => {
      const error = new AxiosError('Conflict', 'ERR_CONFLICT', undefined, undefined, {
        status: 409,
        statusText: 'Conflict',
        headers: { 'x-request-id': 'header-req-id' },
        config: { headers: new AxiosHeaders() },
        data: {
          title: 'Conflict Detected',
        },
      });

      const normalized = normalizeApiError(error);
      expect(normalized.title).toBe('Conflict Detected');
      expect(normalized.status).toBe(409);
      expect(normalized.requestId).toBe('header-req-id');
    });

    it('normalizes standard Error objects', () => {
      const error = new Error('Network timeout');
      const normalized = normalizeApiError(error, '/custom/path');
      expect(normalized).toEqual({
        type: 'about:blank',
        title: 'Internal Server Error',
        status: 500,
        detail: 'Network timeout',
        instance: '/custom/path',
        requestId: 'unknown',
      });
    });

    it('normalizes non-error throwables', () => {
      const normalized = normalizeApiError('Something went wrong');
      expect(normalized).toEqual({
        type: 'about:blank',
        title: 'Internal Server Error',
        status: 500,
        detail: 'An unexpected error occurred',
        instance: '/api',
        requestId: 'unknown',
      });
    });
  });

  describe('server api utilities', () => {
    const originalWindow = (globalThis as unknown as { window?: unknown }).window;

    afterEach(() => {
      if (originalWindow === undefined) {
        delete (globalThis as unknown as { window?: unknown }).window;
      } else {
        (globalThis as unknown as { window?: unknown }).window = originalWindow;
      }
    });

    it('resolves default server api base url when env is empty', () => {
      expect(resolveServerApiBaseUrl({})).toBe('http://127.0.0.1:3001');
    });

    it('resolves custom server api base url from env with trailing slash trimmed', () => {
      expect(resolveServerApiBaseUrl({ API_BASE_URL: 'http://api.internal:3001/' })).toBe(
        'http://api.internal:3001',
      );
      expect(resolveServerApiBaseUrl({ API_BASE_URL: '  https://custom-api.com/// ' })).toBe(
        'https://custom-api.com',
      );
    });

    it('throws error when resolveServerApiBaseUrl is called in browser environment', () => {
      (globalThis as unknown as { window: unknown }).window = {};
      expect(() => resolveServerApiBaseUrl({})).toThrow(
        'resolveServerApiBaseUrl must only be called on the server',
      );
    });

    it('creates server api client with and without requestId', () => {
      const clientWithId = createServerApiClient('custom-request-id');
      expect(clientWithId.defaults.baseURL).toBe('http://127.0.0.1:3001');
      expect(clientWithId.defaults.timeout).toBe(10_000);
      expect(clientWithId.defaults.headers['X-Request-Id']).toBe('custom-request-id');

      const clientWithoutId = createServerApiClient();
      expect(clientWithoutId.defaults.headers['X-Request-Id']).toBeUndefined();

      const clientWithEmptyId = createServerApiClient('   ');
      expect(clientWithEmptyId.defaults.headers['X-Request-Id']).toBeUndefined();
    });
  });
});
