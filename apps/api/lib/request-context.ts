import { randomUUID } from 'node:crypto';

export const REQUEST_ID_HEADER = 'X-Request-Id';
export const MAX_REQUEST_ID_HEADER_LENGTH = 64;

/**
 * Canonical RFC 9562 / RFC 4122 UUID (versions 1–8, RFC variant 8/9/a/b).
 */
export const CANONICAL_UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type RequestContext = Readonly<{
  requestId: string;
  instance: string;
}>;

const requestContextCache = new WeakMap<Request, RequestContext>();

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
  return typeof candidate.requestId === 'string' && typeof candidate.instance === 'string';
}

export function resolveRequestContext(requestOrContext: Request | RequestContext): RequestContext {
  if (isRequestContext(requestOrContext)) {
    return requestOrContext;
  }

  const cached = requestContextCache.get(requestOrContext);
  if (cached !== undefined) {
    return cached;
  }

  const context: RequestContext = Object.freeze({
    requestId: normalizeRequestId(requestOrContext.headers.get('x-request-id')),
    instance: extractInstancePath(requestOrContext.url),
  });
  requestContextCache.set(requestOrContext, context);
  return context;
}
