import { afterEach, describe, expect, it } from 'vitest';
import {
  DELETE as deleteHealth,
  GET as getHealth,
  HEAD as headHealth,
  OPTIONS as optionsHealth,
  PATCH as patchHealth,
  POST as postHealth,
  PUT as putHealth,
} from './health/route';
import { GET as getOpenApi, HEAD as headOpenApi, POST as postOpenApi } from './api/openapi/route';
import { GET as getDocs, HEAD as headDocs, POST as postDocs } from './docs/route';
import {
  DELETE as deleteCatchAll,
  GET as getCatchAll,
  HEAD as headCatchAll,
  POST as postCatchAll,
} from './[[...slug]]/route';

const ORIGINAL_ENV = { ...process.env };

function setTestEnv(overrides: Record<string, string | undefined>): void {
  process.env = { ...ORIGINAL_ENV };
  for (const [key, value] of Object.entries(overrides)) {
    if (value === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = value;
    }
  }
}

function encodeBasicAuth(username: string, password: string): string {
  return `Basic ${Buffer.from(`${username}:${password}`, 'utf8').toString('base64')}`;
}

afterEach(() => {
  process.env = { ...ORIGINAL_ENV };
});

describe('/health route handler', () => {
  it('returns 200 wrapped HealthResponse with requestId and Cache-Control: no-store', async () => {
    const requestId = 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b';
    const request = new Request('http://127.0.0.1:3001/health', {
      headers: { 'x-request-id': requestId },
    });

    const response = await getHealth(request);
    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toContain('application/json');
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(response.headers.get('x-request-id')).toBe(requestId);

    const payload = await response.json();
    expect(payload).toEqual({
      data: {
        status: 'ok',
        service: 'api',
      },
      meta: {
        requestId,
      },
    });
  });

  it('remains public in production even when docs are disabled or misconfigured', async () => {
    setTestEnv({
      NODE_ENV: 'production',
      DOCS_ENABLED: 'INVALID_VALUE',
      DOCS_USERNAME: '',
      DOCS_PASSWORD: '',
    });

    const response = await getHealth(new Request('http://127.0.0.1:3001/health'));
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.data).toEqual({ status: 'ok', service: 'api' });
  });

  it('supports HEAD /health with empty body and identical headers', async () => {
    const requestId = 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b';
    const response = await headHealth(
      new Request('http://127.0.0.1:3001/health', {
        method: 'HEAD',
        headers: { 'x-request-id': requestId },
      }),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('x-request-id')).toBe(requestId);
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(await response.text()).toBe('');
  });

  it('returns 405 ProblemDetails with Allow: GET, HEAD on unsupported methods', async () => {
    const handlers = [
      { method: 'POST', fn: postHealth },
      { method: 'PUT', fn: putHealth },
      { method: 'PATCH', fn: patchHealth },
      { method: 'DELETE', fn: deleteHealth },
      { method: 'OPTIONS', fn: optionsHealth },
    ] as const;

    for (const { method, fn } of handlers) {
      const response = await fn(
        new Request('http://127.0.0.1:3001/health?debug=true', {
          method,
          headers: { 'x-request-id': 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b' },
        }),
      );
      expect(response.status).toBe(405);
      expect(response.headers.get('allow')).toBe('GET, HEAD');
      expect(response.headers.get('content-type')).toContain('application/problem+json');
      expect(response.headers.get('x-request-id')).toBe('b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b');
      expect(await response.json()).toEqual({
        type: 'about:blank',
        title: 'Method Not Allowed',
        status: 405,
        detail: 'The HTTP method is not allowed for this resource.',
        instance: '/health',
        requestId: 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b',
      });
    }
  });
});

describe('catch-all 404 route handler', () => {
  it('returns sanitized 404 ProblemDetails without reflecting query strings or unknown path input', async () => {
    const request = new Request(
      'http://127.0.0.1:3001/api/health?token=secret-jwt&sql=DROP_TABLE',
      {
        headers: { 'x-request-id': 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b' },
      },
    );

    const response = await getCatchAll(request);
    expect(response.status).toBe(404);
    expect(response.headers.get('content-type')).toContain('application/problem+json');
    expect(response.headers.get('x-request-id')).toBe('b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b');

    const text = await response.text();
    expect(text).not.toContain('secret-jwt');
    expect(text).not.toContain('DROP_TABLE');

    expect(JSON.parse(text)).toEqual({
      type: 'about:blank',
      title: 'Not Found',
      status: 404,
      detail: 'The requested resource was not found.',
      instance: '/api/health',
      requestId: 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b',
    });

    const postResponse = await postCatchAll(
      new Request('http://127.0.0.1:3001/nonexistent', { method: 'POST' }),
    );
    expect(postResponse.status).toBe(404);

    const deleteResponse = await deleteCatchAll(
      new Request('http://127.0.0.1:3001/nonexistent', { method: 'DELETE' }),
    );
    expect(deleteResponse.status).toBe(404);

    const headResponse = await headCatchAll(
      new Request('http://127.0.0.1:3001/nonexistent', { method: 'HEAD' }),
    );
    expect(headResponse.status).toBe(404);
    expect(await headResponse.text()).toBe('');
  });
});

describe('/api/openapi and /docs routes and docs security gate', () => {
  it('serves raw OpenAPI 3.1.0 schema and pinned Scalar HTML by default in development/test', async () => {
    setTestEnv({
      NODE_ENV: 'test',
      DOCS_ENABLED: undefined,
    });

    const schemaRes = await getOpenApi(new Request('http://127.0.0.1:3001/api/openapi'));
    expect(schemaRes.status).toBe(200);
    expect(schemaRes.headers.get('cache-control')).toBe('private, no-store');
    expect(schemaRes.headers.get('vary')).toBe('Authorization');
    expect(schemaRes.headers.get('x-request-id')).toMatch(/^[0-9a-f-]{36}$/);

    const spec = (await schemaRes.json()) as Record<string, unknown>;
    expect(spec.openapi).toBe('3.1.0');
    expect(spec).not.toHaveProperty('data');
    expect(spec).not.toHaveProperty('meta');

    const paths = spec.paths as Record<string, Record<string, unknown>>;
    expect(paths['/health']).toBeDefined();
    expect((paths['/health']?.get as Record<string, unknown>)?.security).toEqual([]);

    const components = spec.components as Record<string, Record<string, unknown>>;
    expect(components.schemas?.HealthData).toBeDefined();
    expect(components.schemas?.ApiMeta).toBeDefined();
    expect(components.schemas?.PaginationMeta).toBeDefined();
    expect(components.schemas?.HealthResponse).toBeDefined();
    expect(components.schemas?.ValidationIssue).toBeDefined();
    expect(components.schemas?.ProblemDetails).toBeDefined();
    expect(components.securitySchemes?.DocsBasicAuth).toMatchObject({
      type: 'http',
      scheme: 'basic',
    });

    const docsRes = await getDocs(new Request('http://127.0.0.1:3001/docs'));
    expect(docsRes.status).toBe(200);
    expect(docsRes.headers.get('content-type')).toContain('text/html');
    expect(docsRes.headers.get('cache-control')).toBe('private, no-store');
    expect(docsRes.headers.get('vary')).toBe('Authorization');
    expect(docsRes.headers.get('x-request-id')).toMatch(/^[0-9a-f-]{36}$/);

    const headSchemaRes = await headOpenApi(
      new Request('http://127.0.0.1:3001/api/openapi', { method: 'HEAD' }),
    );
    expect(headSchemaRes.status).toBe(200);
    expect(headSchemaRes.headers.get('cache-control')).toBe('private, no-store');
    expect(headSchemaRes.headers.get('vary')).toBe('Authorization');
    expect(await headSchemaRes.text()).toBe('');

    const headDocsRes = await headDocs(
      new Request('http://127.0.0.1:3001/docs', { method: 'HEAD' }),
    );
    expect(headDocsRes.status).toBe(200);
    expect(headDocsRes.headers.get('cache-control')).toBe('private, no-store');
    expect(headDocsRes.headers.get('vary')).toBe('Authorization');
    expect(await headDocsRes.text()).toBe('');
  });

  it('returns 404 ProblemDetails when DOCS_ENABLED=false or by default in production', async () => {
    setTestEnv({
      NODE_ENV: 'development',
      DOCS_ENABLED: 'false',
    });

    for (const [path, handler] of [
      ['/docs', getDocs],
      ['/api/openapi', getOpenApi],
    ] as const) {
      const res = await handler(new Request(`http://127.0.0.1:3001${path}`));
      expect(res.status).toBe(404);
      expect(res.headers.get('cache-control')).toBe('private, no-store');
      expect(res.headers.get('vary')).toBe('Authorization');
      const problem = await res.json();
      expect(problem.status).toBe(404);
      expect(problem.instance).toBe(path);
    }

    setTestEnv({
      NODE_ENV: 'production',
      DOCS_ENABLED: undefined,
    });

    for (const [path, handler] of [
      ['/docs', getDocs],
      ['/api/openapi', getOpenApi],
    ] as const) {
      const res = await handler(new Request(`http://127.0.0.1:3001${path}`));
      expect(res.status).toBe(404);
      expect(res.headers.get('cache-control')).toBe('private, no-store');
      expect(res.headers.get('vary')).toBe('Authorization');
    }
  });

  it.each(['TRUE', 'FALSE', 'True', 'False', '1', '0', 'yes', 'no', 'invalid'])(
    'returns 500 generic ProblemDetails when DOCS_ENABLED has invalid non-empty value %j',
    async (invalidValue) => {
      setTestEnv({
        NODE_ENV: 'development',
        DOCS_ENABLED: invalidValue,
      });

      const docsRes = await getDocs(new Request('http://127.0.0.1:3001/docs'));
      expect(docsRes.status).toBe(500);
      expect(docsRes.headers.get('cache-control')).toBe('private, no-store');
      expect(docsRes.headers.get('vary')).toBe('Authorization');
      expect(await docsRes.json()).toMatchObject({
        type: 'about:blank',
        title: 'Internal Server Error',
        status: 500,
        detail: 'An unexpected error occurred.',
        instance: '/docs',
      });

      const schemaRes = await getOpenApi(new Request('http://127.0.0.1:3001/api/openapi'));
      expect(schemaRes.status).toBe(500);
      expect(schemaRes.headers.get('cache-control')).toBe('private, no-store');
      expect(schemaRes.headers.get('vary')).toBe('Authorization');
    },
  );

  it.each([
    { username: '', password: 'a'.repeat(32) },
    { username: '   ', password: 'a'.repeat(32) },
    { username: 'admin:ops', password: 'a'.repeat(32) },
    { username: 'admin\nops', password: 'a'.repeat(32) },
    { username: 'admin', password: '' },
    { username: 'admin', password: 'a'.repeat(31) },
    { username: 'admin', password: `${'a'.repeat(32)}\n` },
  ])(
    'fails closed with 500 generic ProblemDetails in production when DOCS_ENABLED=true but credentials are misconfigured (%j)',
    async ({ username, password }) => {
      setTestEnv({
        NODE_ENV: 'production',
        DOCS_ENABLED: 'true',
        DOCS_USERNAME: username,
        DOCS_PASSWORD: password,
      });

      const docsRes = await getDocs(new Request('http://127.0.0.1:3001/docs'));
      expect(docsRes.status).toBe(500);
      expect(docsRes.headers.get('cache-control')).toBe('private, no-store');
      expect(docsRes.headers.get('vary')).toBe('Authorization');
      const body = await docsRes.json();
      expect(body.detail).toBe('An unexpected error occurred.');
      expect(JSON.stringify(body)).not.toContain(password || 'placeholder');
    },
  );

  it('enforces HTTP Basic authentication in production when DOCS_ENABLED=true and credentials are valid', async () => {
    const validUser = 'catering-docs-admin';
    const validPass = 's3cure-p4ssw0rd-with-at-least-32-chars!!';
    setTestEnv({
      NODE_ENV: 'production',
      DOCS_ENABLED: 'true',
      DOCS_USERNAME: validUser,
      DOCS_PASSWORD: validPass,
    });

    // Missing Authorization header -> 401
    const unauthRes = await getDocs(new Request('http://127.0.0.1:3001/docs'));
    expect(unauthRes.status).toBe(401);
    expect(unauthRes.headers.get('www-authenticate')).toBe(
      'Basic realm="Smart Catering Docs", charset="UTF-8"',
    );
    expect(unauthRes.headers.get('cache-control')).toBe('private, no-store');
    expect(unauthRes.headers.get('vary')).toBe('Authorization');

    // Wrong password -> 401
    const wrongPassRes = await getOpenApi(
      new Request('http://127.0.0.1:3001/api/openapi', {
        headers: {
          authorization: encodeBasicAuth(validUser, 'wrong-password-with-at-least-32-chars!!'),
        },
      }),
    );
    expect(wrongPassRes.status).toBe(401);
    expect(wrongPassRes.headers.get('www-authenticate')).toBe(
      'Basic realm="Smart Catering Docs", charset="UTF-8"',
    );

    // Malformed Basic header -> 401
    const malformedRes = await getOpenApi(
      new Request('http://127.0.0.1:3001/api/openapi', {
        headers: {
          authorization: 'Basic !!!not_base64!!!',
        },
      }),
    );
    expect(malformedRes.status).toBe(401);

    // Correct credentials -> 200 and no credentials leaked into HTML or OpenAPI JSON
    const authHeader = encodeBasicAuth(validUser, validPass);
    const okDocsRes = await getDocs(
      new Request('http://127.0.0.1:3001/docs', {
        headers: { authorization: authHeader },
      }),
    );
    expect(okDocsRes.status).toBe(200);
    const docsHtml = await okDocsRes.text();
    expect(docsHtml).not.toContain(validUser);
    expect(docsHtml).not.toContain(validPass);

    const okSchemaRes = await getOpenApi(
      new Request('http://127.0.0.1:3001/api/openapi', {
        headers: { authorization: authHeader },
      }),
    );
    expect(okSchemaRes.status).toBe(200);
    const schemaText = await okSchemaRes.text();
    expect(schemaText).not.toContain(validUser);
    expect(schemaText).not.toContain(validPass);
  });

  it('returns 405 ProblemDetails with private, no-store and Vary: Authorization on POST /docs and POST /api/openapi', async () => {
    for (const [path, handler] of [
      ['/docs', postDocs],
      ['/api/openapi', postOpenApi],
    ] as const) {
      const res = await handler(new Request(`http://127.0.0.1:3001${path}`, { method: 'POST' }));
      expect(res.status).toBe(405);
      expect(res.headers.get('allow')).toBe('GET, HEAD');
      expect(res.headers.get('cache-control')).toBe('private, no-store');
      expect(res.headers.get('vary')).toBe('Authorization');
    }
  });
});
