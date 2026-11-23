import { randomUUID } from 'node:crypto';
import type { Request as ExpressRequest } from 'express';

export const REQUEST_ID_HEADER = 'X-Request-Id';
export const MAX_REQUEST_ID_HEADER_LENGTH = 64;

export const CANONICAL_UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type RequestContext = Readonly<{
  requestId: string;
  instance: string;
}>;

const requestContextCache = new WeakMap<object, RequestContext>();

export function isValidRequestId(value: unknown): value is string {
  if (typeof value !== 'string') {
    return false;
  }
  if (value.length !== 36) {
    return false;
  }
  return CANONICAL_UUID_REGEX.test(value);
}

export function normalizeRequestId(rawHeader?: string | null): string {
  if (typeof rawHeader === 'string' && rawHeader.length <= MAX_REQUEST_ID_HEADER_LENGTH) {
    const candidate = rawHeader.trim().toLowerCase();
    if (isValidRequestId(candidate)) {
      return candidate;
    }
  }
  return randomUUID().toLowerCase();
}

export function extractInstancePath(urlOrPath: string | URL): string {
  if (urlOrPath instanceof URL) {
    return urlOrPath.pathname || '/';
  }
  try {
    const parsed = new URL(urlOrPath, 'http://127.0.0.1');
    return parsed.pathname || '/';
  } catch {
    const queryIndex = urlOrPath.indexOf('?');
    const hashIndex = urlOrPath.indexOf('#');
    const cutIndex =
      queryIndex >= 0 && hashIndex >= 0
        ? Math.min(queryIndex, hashIndex)
        : queryIndex >= 0
          ? queryIndex
          : hashIndex;
    const rawPath = cutIndex >= 0 ? urlOrPath.slice(0, cutIndex) : urlOrPath;
    return rawPath.startsWith('/') ? rawPath : '/';
  }
}

export function isRequestContext(value: unknown): value is RequestContext {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return typeof candidate['requestId'] === 'string' && typeof candidate['instance'] === 'string';
}

export function resolveRequestContext(
  requestOrContext: Request | ExpressRequest | RequestContext | object,
): RequestContext {
  if (isRequestContext(requestOrContext)) {
    return requestOrContext;
  }

  const cached = requestContextCache.get(requestOrContext);
  if (cached !== undefined) {
    return cached;
  }

  let rawHeader: string | null | undefined;
  let rawUrl: string | URL = '/';

  if (requestOrContext instanceof Request) {
    rawHeader = requestOrContext.headers.get('x-request-id');
    rawUrl = requestOrContext.url;
  } else if (typeof requestOrContext === 'object' && requestOrContext !== null) {
    const candidate = requestOrContext as Record<string, unknown>;
    if (typeof candidate['get'] === 'function') {
      rawHeader = (candidate['get'] as (header: string) => string | undefined)('x-request-id');
    } else if (candidate['headers'] && typeof candidate['headers'] === 'object') {
      const headers = candidate['headers'] as Record<string, unknown>;
      rawHeader = (headers['x-request-id'] ?? headers['X-Request-Id']) as string | undefined;
    }
    rawUrl = (candidate['originalUrl'] ?? candidate['url'] ?? '/') as string;
  }

  const context: RequestContext = Object.freeze({
    requestId: normalizeRequestId(rawHeader),
    instance: extractInstancePath(rawUrl),
  });

  requestContextCache.set(requestOrContext, context);
  return context;
}
