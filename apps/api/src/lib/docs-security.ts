import { createHash, timingSafeEqual } from 'node:crypto';
import type {
  Request as ExpressRequest,
  Response as ExpressResponse,
  NextFunction,
  RequestHandler,
} from 'express';
import {
  createInternalServerError,
  createMethodNotAllowedError,
  createNotFoundError,
  createUnauthorizedError,
} from './errors.js';

export const DOCS_BASIC_REALM = 'Basic realm="Smart Catering Docs", charset="UTF-8"';
export const SCALAR_CDN_URL = 'https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.76.4';
export const MIN_DOCS_PASSWORD_CODEPOINTS = 32;

export const DOCS_SECURITY_HEADERS = Object.freeze({
  'Cache-Control': 'private, no-store',
  Vary: 'Authorization',
} as const);

const STRICT_BASE64_REGEX = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
const CRLF_REGEX = /[\r\n]/;

export type DocsEnvironment = Readonly<Record<string, string | undefined>>;

function getRuntimeEnv(envOverride?: DocsEnvironment): DocsEnvironment {
  return envOverride ?? process.env;
}

export function constantTimeEqualUtf8(left: string, right: string): boolean {
  const leftDigest = createHash('sha256').update(left, 'utf8').digest();
  const rightDigest = createHash('sha256').update(right, 'utf8').digest();
  return timingSafeEqual(leftDigest, rightDigest);
}

function isValidConfiguredUsername(username: string): boolean {
  if (username.trim().length === 0) {
    return false;
  }
  if (username.includes(':') || CRLF_REGEX.test(username)) {
    return false;
  }
  return true;
}

function isValidConfiguredPassword(password: string): boolean {
  if (CRLF_REGEX.test(password)) {
    return false;
  }
  const codepoints = password[Symbol.iterator]();
  for (let count = 0; count < MIN_DOCS_PASSWORD_CODEPOINTS; count += 1) {
    if (codepoints.next().done) return false;
  }
  return true;
}

export function parseBasicAuthHeader(
  rawHeader: string | null | undefined,
): Readonly<{ username: string; password: string }> | null {
  if (typeof rawHeader !== 'string' || CRLF_REGEX.test(rawHeader)) {
    return null;
  }

  const trimmed = rawHeader.trim();
  if (trimmed.length < 7 || trimmed.slice(0, 6).toLowerCase() !== 'basic ') {
    return null;
  }

  const encoded = trimmed.slice(6).trim();
  if (encoded.length === 0 || encoded.length % 4 !== 0 || !STRICT_BASE64_REGEX.test(encoded)) {
    return null;
  }

  let decoded: string;
  try {
    const bytes = Buffer.from(encoded, 'base64');
    decoded = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes);
  } catch {
    return null;
  }

  if (CRLF_REGEX.test(decoded)) {
    return null;
  }

  const colonIndex = decoded.indexOf(':');
  if (colonIndex < 0) {
    return null;
  }

  return Object.freeze({
    username: decoded.slice(0, colonIndex),
    password: decoded.slice(colonIndex + 1),
  });
}

function extractAuthorizationHeader(target: unknown): string | null | undefined {
  if (target instanceof Request) {
    return target.headers.get('authorization');
  }
  if (typeof target === 'object' && target !== null) {
    const candidate = target as Record<string, unknown>;
    if (typeof candidate['get'] === 'function') {
      return (candidate['get'] as (name: string) => string | undefined)('authorization');
    }
    if (candidate['headers'] && typeof candidate['headers'] === 'object') {
      const headers = candidate['headers'] as Record<string, unknown>;
      return (headers['authorization'] ?? headers['Authorization']) as string | undefined;
    }
  }
  return undefined;
}

export function evaluateDocsAccess(request: unknown, envOverride?: DocsEnvironment): void {
  const env = getRuntimeEnv(envOverride);
  const rawNodeEnv = env['NODE_ENV']?.trim() ?? 'development';
  const isDevOrTest = rawNodeEnv === 'development' || rawNodeEnv === 'test';
  const isProduction = rawNodeEnv === 'production';

  if (!isDevOrTest && !isProduction) {
    throw createInternalServerError();
  }

  const rawDocsEnabled = env['DOCS_ENABLED'];
  let docsEnabled: boolean;

  if (rawDocsEnabled === undefined || rawDocsEnabled.trim() === '') {
    docsEnabled = isDevOrTest;
  } else {
    const trimmedEnabled = rawDocsEnabled.trim();
    if (trimmedEnabled === 'true') {
      docsEnabled = true;
    } else if (trimmedEnabled === 'false') {
      docsEnabled = false;
    } else {
      throw createInternalServerError();
    }
  }

  if (!docsEnabled) {
    throw createNotFoundError();
  }

  if (isProduction) {
    const expectedUsername = env['DOCS_USERNAME'] ?? '';
    const expectedPassword = env['DOCS_PASSWORD'] ?? '';

    if (
      !isValidConfiguredUsername(expectedUsername) ||
      !isValidConfiguredPassword(expectedPassword)
    ) {
      throw createInternalServerError();
    }

    const authHeader = extractAuthorizationHeader(request);
    const parsedCredentials = parseBasicAuthHeader(authHeader);
    const candidateUsername = parsedCredentials?.username ?? '';
    const candidatePassword = parsedCredentials?.password ?? '';

    const usernameMatches = constantTimeEqualUtf8(candidateUsername, expectedUsername);
    const passwordMatches = constantTimeEqualUtf8(candidatePassword, expectedPassword);

    if (parsedCredentials === null || !usernameMatches || !passwordMatches) {
      throw createUnauthorizedError(
        'Valid HTTP Basic authentication credentials are required to access API documentation.',
        { 'WWW-Authenticate': DOCS_BASIC_REALM },
      );
    }
  }
}

export function docsSecurityMiddleware(envOverride?: DocsEnvironment): RequestHandler {
  return (req: ExpressRequest, res: ExpressResponse, next: NextFunction): void => {
    try {
      evaluateDocsAccess(req, envOverride);

      const originalSetHeader = res.setHeader.bind(res);
      res.setHeader = function (
        name: string,
        value: string | number | readonly string[],
      ): ExpressResponse {
        const lower = name.toLowerCase();
        if (lower === 'cache-control') {
          return originalSetHeader('Cache-Control', DOCS_SECURITY_HEADERS['Cache-Control']);
        }
        if (lower === 'vary') {
          return originalSetHeader('Vary', DOCS_SECURITY_HEADERS.Vary);
        }
        return originalSetHeader(name, value);
      };

      const originalWriteHead = res.writeHead.bind(res);
      res.writeHead = function (statusCode: number, ...args: unknown[]): ExpressResponse {
        originalSetHeader('Cache-Control', DOCS_SECURITY_HEADERS['Cache-Control']);
        originalSetHeader('Vary', DOCS_SECURITY_HEADERS.Vary);
        return (originalWriteHead as (...a: unknown[]) => ExpressResponse)(statusCode, ...args);
      };

      res.setHeader('Cache-Control', DOCS_SECURITY_HEADERS['Cache-Control']);
      res.setHeader('Vary', DOCS_SECURITY_HEADERS.Vary);

      next();
    } catch (error) {
      res.setHeader('Cache-Control', DOCS_SECURITY_HEADERS['Cache-Control']);
      res.setHeader('Vary', DOCS_SECURITY_HEADERS.Vary);
      next(error);
    }
  };
}

export function docsMethodNotAllowedHandler(): RequestHandler {
  return (_req: ExpressRequest, res: ExpressResponse, next: NextFunction): void => {
    res.setHeader('Cache-Control', DOCS_SECURITY_HEADERS['Cache-Control']);
    res.setHeader('Vary', DOCS_SECURITY_HEADERS.Vary);
    next(createMethodNotAllowedError(['GET', 'HEAD']));
  };
}
