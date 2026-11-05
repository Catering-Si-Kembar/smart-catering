import { createHash, timingSafeEqual } from 'node:crypto';
import {
  createInternalServerError,
  createMethodNotAllowedError,
  createNotFoundError,
  createUnauthorizedError,
} from './errors';
import { type ApiRouteHandler, withApiRoute } from './route-handler';

export const DOCS_BASIC_REALM = 'Basic realm="Smart Catering Docs", charset="UTF-8"';
export const SCALAR_CDN_URL = 'https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.76.4';
export const MIN_DOCS_PASSWORD_CODEPOINTS = 32;

export const DOCS_SECURITY_HEADERS: Readonly<Record<string, string>> = Object.freeze({
  'Cache-Control': 'private, no-store',
  Vary: 'Authorization',
});

const STRICT_BASE64_REGEX = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
const CRLF_REGEX = /[\r\n]/;

type DocsEnvironment = Readonly<Record<string, string | undefined>>;

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

function parseBasicAuthHeader(
  rawHeader: string | null,
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

export function evaluateDocsAccess(request: Request, envOverride?: DocsEnvironment): void {
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

    const parsedCredentials = parseBasicAuthHeader(request.headers.get('authorization'));
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

function enforceDocsHeaders(response: Response): Response {
  if (
    response.headers.get('cache-control') === 'private, no-store' &&
    response.headers.get('vary') === 'Authorization'
  )
    return response;
  const headers = new Headers(response.headers);
  headers.set('Cache-Control', 'private, no-store');
  headers.set('Vary', 'Authorization');
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

export function withDocsSecurity(
  handler: ApiRouteHandler,
  envOverride?: DocsEnvironment,
): (request: Request, routeContext?: unknown) => Promise<Response> {
  const wrapped = withApiRoute(
    (request, context, routeContext) => {
      evaluateDocsAccess(request, envOverride);
      return handler(request, context, routeContext);
    },
    {
      allowedMethods: ['GET', 'HEAD'],
      defaultHeaders: DOCS_SECURITY_HEADERS,
    },
  );

  return async function docsGuardedRoute(
    request: Request,
    routeContext?: unknown,
  ): Promise<Response> {
    const response = await wrapped(request, routeContext);
    return enforceDocsHeaders(response);
  };
}

export function createDocsMethodNotAllowedHandler(): (request: Request) => Promise<Response> {
  const wrapped = withApiRoute(
    () => {
      throw createMethodNotAllowedError(['GET', 'HEAD']);
    },
    {
      defaultHeaders: DOCS_SECURITY_HEADERS,
    },
  );

  return async function docsMethodNotAllowed(request: Request): Promise<Response> {
    const response = await wrapped(request);
    return enforceDocsHeaders(response);
  };
}
