import type { Server } from 'node:http';
import { afterEach, describe, expect, it } from 'vitest';
import { createApiApp } from './app.js';
import type { HealthResponse, ProblemDetails } from '@smart-catering/types';

let activeServer: Server | undefined;

afterEach(async () => {
  if (activeServer) {
    await new Promise<void>((resolveClose) => activeServer!.close(() => resolveClose()));
    activeServer = undefined;
  }
});

async function startApi(
  envOverride?: Record<string, string | undefined>,
): Promise<{ port: number; origin: string }> {
  const app = createApiApp(envOverride);
  return new Promise((resolveListening) => {
    activeServer = app.listen(0, '127.0.0.1', () => {
      const address = activeServer!.address();
      const port = typeof address === 'object' && address ? address.port : 0;
      resolveListening({ port, origin: `http://127.0.0.1:${port}` });
    });
  });
}

function encodeBasicAuth(username: string, password: string): string {
  return `Basic ${Buffer.from(`${username}:${password}`, 'utf8').toString('base64')}`;
}

describe('/health routes', () => {
  it('returns 200 wrapped HealthResponse with requestId and Cache-Control: no-store', async () => {
    const requestId = 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b';
    const { origin } = await startApi();

    const response = await fetch(`${origin}/health`, {
      headers: { 'x-request-id': requestId },
    });

    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toContain('application/json');
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(response.headers.get('x-request-id')).toBe(requestId);

    const payload = (await response.json()) as HealthResponse;
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

  it('supports HEAD /health with empty body and identical headers', async () => {
    const requestId = 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b';
    const { origin } = await startApi();

    const response = await fetch(`${origin}/health`, {
      method: 'HEAD',
      headers: { 'x-request-id': requestId },
    });

    expect(response.status).toBe(200);
    expect(response.headers.get('x-request-id')).toBe(requestId);
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(await response.text()).toBe('');
  });

  it('returns 405 ProblemDetails with Allow: GET, HEAD on unsupported methods', async () => {
    const { origin } = await startApi();
    const unsupportedMethods = ['POST', 'PUT', 'PATCH', 'DELETE'];

    for (const method of unsupportedMethods) {
      const response = await fetch(`${origin}/health`, { method });
      expect(response.status).toBe(405);
      expect(response.headers.get('allow')).toBe('GET, HEAD');
      expect(response.headers.get('content-type')).toContain('application/problem+json');

      const problem = (await response.json()) as ProblemDetails;
      expect(problem.status).toBe(405);
      expect(problem.title).toBe('Method Not Allowed');
    }

    const emptyJsonRes = await fetch(`${origin}/health`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '',
    });
    expect(emptyJsonRes.status).toBe(400);
  });

  it('remains public in production even when docs are misconfigured', async () => {
    const { origin } = await startApi({
      NODE_ENV: 'production',
      DOCS_ENABLED: 'INVALID_VALUE',
      DOCS_USERNAME: '',
      DOCS_PASSWORD: '',
    });

    const response = await fetch(`${origin}/health`);
    expect(response.status).toBe(200);
    const payload = (await response.json()) as HealthResponse;
    expect(payload.data).toEqual({ status: 'ok', service: 'api' });
  });
});

describe('/api/v1/health route', () => {
  it('returns 200 wrapped HealthResponse and supports HEAD and 405 on unsupported methods', async () => {
    const requestId = 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b';
    const { origin } = await startApi();

    const getRes = await fetch(`${origin}/api/v1/health`, {
      headers: { 'x-request-id': requestId },
    });
    expect(getRes.status).toBe(200);
    expect(getRes.headers.get('x-request-id')).toBe(requestId);
    const getPayload = (await getRes.json()) as HealthResponse;
    expect(getPayload.data).toEqual({ status: 'ok', service: 'api' });

    const headRes = await fetch(`${origin}/api/v1/health`, {
      method: 'HEAD',
      headers: { 'x-request-id': requestId },
    });
    expect(headRes.status).toBe(200);
    expect(await headRes.text()).toBe('');

    const postRes = await fetch(`${origin}/api/v1/health`, { method: 'POST' });
    expect(postRes.status).toBe(405);
    expect(postRes.headers.get('allow')).toBe('GET, HEAD');
  });
});

describe('/api/openapi route', () => {
  it('returns raw OpenAPI 3.1.0 document in dev/test', async () => {
    const { origin } = await startApi({ NODE_ENV: 'test', DOCS_ENABLED: 'true' });
    const response = await fetch(`${origin}/api/openapi`);

    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toContain('application/json');
    expect(response.headers.get('cache-control')).toBe('private, no-store');
    expect(response.headers.get('vary')).toBe('Authorization');

    const schema = (await response.json()) as { openapi: string; paths: Record<string, unknown> };
    expect(schema.openapi).toBe('3.1.0');
    expect(schema.paths['/health']).toBeDefined();
    expect(schema.paths['/api/v1/health']).toBeDefined();
  });

  it('supports HEAD /api/openapi and 405 on unsupported methods', async () => {
    const { origin } = await startApi({ NODE_ENV: 'test', DOCS_ENABLED: 'true' });

    const headRes = await fetch(`${origin}/api/openapi`, { method: 'HEAD' });
    expect(headRes.status).toBe(200);
    expect(await headRes.text()).toBe('');

    const postRes = await fetch(`${origin}/api/openapi`, { method: 'POST' });
    expect(postRes.status).toBe(405);
    expect(postRes.headers.get('allow')).toBe('GET, HEAD');
    expect(postRes.headers.get('cache-control')).toBe('private, no-store');
    expect(postRes.headers.get('vary')).toBe('Authorization');
  });
});

describe('/docs route', () => {
  it('renders Scalar HTML documentation in dev/test', async () => {
    const { origin } = await startApi({ NODE_ENV: 'test', DOCS_ENABLED: 'true' });
    const response = await fetch(`${origin}/docs`);

    expect(response.status).toBe(200);
    expect(response.headers.get('content-type')).toContain('text/html');
    expect(response.headers.get('cache-control')).toBe('private, no-store');
    expect(response.headers.get('vary')).toBe('Authorization');

    const html = await response.text();
    expect(html).toContain('Scalar.createApiReference');
    expect(html).toContain('https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.76.4');
  });

  it('supports HEAD /docs and 405 on unsupported methods', async () => {
    const { origin } = await startApi({ NODE_ENV: 'test', DOCS_ENABLED: 'true' });

    const headRes = await fetch(`${origin}/docs`, { method: 'HEAD' });
    expect(headRes.status).toBe(200);
    expect(await headRes.text()).toBe('');

    const postRes = await fetch(`${origin}/docs`, { method: 'POST' });
    expect(postRes.status).toBe(405);
    expect(postRes.headers.get('allow')).toBe('GET, HEAD');
    expect(postRes.headers.get('cache-control')).toBe('private, no-store');
    expect(postRes.headers.get('vary')).toBe('Authorization');
  });
});

describe('catch-all 404 handler', () => {
  it('returns RFC 9457 ProblemDetails with sanitized instance without query string', async () => {
    const { origin } = await startApi();
    const requestId = 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b';

    const response = await fetch(`${origin}/not-a-route?token=never-echo-this-secret`, {
      headers: { 'x-request-id': requestId },
    });

    expect(response.status).toBe(404);
    expect(response.headers.get('content-type')).toContain('application/problem+json');
    expect(response.headers.get('x-request-id')).toBe(requestId);

    const problem = (await response.json()) as ProblemDetails;
    expect(problem.instance).toBe('/not-a-route');
    expect(problem.status).toBe(404);
    expect(JSON.stringify(problem)).not.toContain('never-echo-this-secret');
  });
});

describe('production docs access control and fail-closed security', () => {
  const validUser = 'smart-catering-admin';
  const validPass = 'a'.repeat(32);

  it('returns 404 when DOCS_ENABLED=false in production', async () => {
    const { origin } = await startApi({
      NODE_ENV: 'production',
      DOCS_ENABLED: 'false',
    });

    for (const path of ['/docs', '/api/openapi']) {
      const response = await fetch(`${origin}${path}`);
      expect(response.status).toBe(404);
      expect(response.headers.get('cache-control')).toBe('private, no-store');
      expect(response.headers.get('vary')).toBe('Authorization');
    }
  });

  it('returns 500 when credentials are misconfigured in production', async () => {
    const { origin } = await startApi({
      NODE_ENV: 'production',
      DOCS_ENABLED: 'true',
      DOCS_USERNAME: 'user',
      DOCS_PASSWORD: 'short-password',
    });

    const response = await fetch(`${origin}/docs`);
    expect(response.status).toBe(500);
    expect(response.headers.get('cache-control')).toBe('private, no-store');
  });

  it('returns 401 with WWW-Authenticate header when credentials are missing or wrong', async () => {
    const { origin } = await startApi({
      NODE_ENV: 'production',
      DOCS_ENABLED: 'true',
      DOCS_USERNAME: validUser,
      DOCS_PASSWORD: validPass,
    });

    const noAuth = await fetch(`${origin}/docs`);
    expect(noAuth.status).toBe(401);
    expect(noAuth.headers.get('www-authenticate')).toContain('Basic realm="Smart Catering Docs"');
    expect(noAuth.headers.get('cache-control')).toBe('private, no-store');

    const wrongAuth = await fetch(`${origin}/docs`, {
      headers: { Authorization: encodeBasicAuth(validUser, 'wrong-password'.padEnd(32, 'x')) },
    });
    expect(wrongAuth.status).toBe(401);
  });

  it('returns 200 when valid Basic auth credentials are provided', async () => {
    const { origin } = await startApi({
      NODE_ENV: 'production',
      DOCS_ENABLED: 'true',
      DOCS_USERNAME: validUser,
      DOCS_PASSWORD: validPass,
    });

    const response = await fetch(`${origin}/docs`, {
      headers: { Authorization: encodeBasicAuth(validUser, validPass) },
    });
    expect(response.status).toBe(200);
    expect(response.headers.get('cache-control')).toBe('private, no-store');

    const html = await response.text();
    expect(html).not.toContain(validPass);
  });
});
