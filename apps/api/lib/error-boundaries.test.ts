import { expect, it, vi } from 'vitest';
import { format } from 'node:util';
import { z } from 'zod';
import { withDocsSecurity } from './docs-security';
import { createSuccessResponse } from './responses';
import { withApiRoute } from './route-handler';
import { parseJsonBody, validateQuery } from './validation';

const payloadSchema = z.object({ settings: z.object({ amount: z.number() }).strict() }).strict();

it.each([
  {
    label: 'invalid nested value',
    payload: { settings: { amount: 'PRIVATE_VALUE' } },
    paths: ['settings.amount'],
  },
  {
    label: 'unknown nested and root fields',
    payload: { settings: { amount: 1, extra: 'PRIVATE_VALUE' }, extra: 'PRIVATE_VALUE' },
    paths: ['extra', 'settings.extra'],
  },
  { label: 'invalid root type', payload: 17, paths: ['$'] },
])(
  'converts native Zod parsing failures to a sanitized 422: $label',
  async ({ payload, paths }) => {
    const handler = withApiRoute(async (request, context) =>
      createSuccessResponse(context, payloadSchema.parse(await parseJsonBody(request))),
    );
    const response = await handler(
      new Request('http://localhost/check?token=PRIVATE_VALUE', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    );
    expect(response.status).toBe(422);
    expect(response.headers.get('content-type')).toContain('application/problem+json');
    const problem = await response.json();
    expect(problem.errors.map((issue: { path: string }) => issue.path).sort()).toEqual(paths);
    expect(problem.requestId).toBe(response.headers.get('x-request-id'));
    expect(problem.instance).toBe('/check');
    expect(JSON.stringify(problem)).not.toContain('PRIVATE_VALUE');
  },
);

it('classifies an empty JSON request as malformed input rather than schema validation', async () => {
  const handler = withApiRoute(async (request, context) =>
    createSuccessResponse(context, payloadSchema.parse(await parseJsonBody(request))),
  );
  const response = await handler(
    new Request('http://localhost/check', { method: 'POST', body: '' }),
  );
  expect(response.status).toBe(400);
  expect(response.headers.get('content-type')).toContain('application/problem+json');
  const problem = await response.json();
  expect(problem.status).toBe(400);
  expect(problem.requestId).toBe(response.headers.get('x-request-id'));
});

it('forces private documentation cache policy even when a renderer supplies public headers', async () => {
  const original = new Response('<!doctype html>', {
    headers: { 'Cache-Control': 'public, max-age=3600', Vary: 'Accept-Encoding' },
  });
  const handler = withDocsSecurity(() => original, { NODE_ENV: 'test', DOCS_ENABLED: 'true' });
  const response = await handler(new Request('http://localhost/docs'));
  expect(response.status).toBe(200);
  expect(response.headers.get('cache-control')).toBe('private, no-store');
  expect(response.headers.get('vary')).toBe('Authorization');
  expect(original.headers.get('cache-control')).toBe('public, max-age=3600');
});

it('logs a correlated server failure without exposing exception secrets or query parameters', async () => {
  const capture = vi.spyOn(console, 'error').mockImplementation(() => {});
  try {
    const handler = withApiRoute(() => {
      throw new Error('SECRET_DATABASE_PASSWORD and private SQL');
    });
    const response = await handler(new Request('http://localhost/failure?token=SECRET_QUERY'));
    expect(response.status).toBe(500);
    const problem = await response.json();
    const logs = capture.mock.calls.map((args) => format(...args)).join('\n');
    expect(logs).toContain(problem.requestId);
    expect(logs).toContain('/failure');
    expect(logs).not.toContain('SECRET_DATABASE_PASSWORD');
    expect(logs).not.toContain('SECRET_QUERY');
    expect(problem.detail).toBe('An unexpected error occurred.');
    expect(problem.requestId).toBe(response.headers.get('x-request-id'));
  } finally {
    capture.mockRestore();
  }
});

it('rejects repeated scalar query parameters instead of silently choosing a value', async () => {
  const querySchema = z.object({ sort: z.enum(['asc', 'desc']) });
  const handler = withApiRoute((request, context) =>
    createSuccessResponse(context, validateQuery(querySchema, new URL(request.url).searchParams)),
  );
  const response = await handler(new Request('http://localhost/check?sort=asc&sort=desc'));
  expect(response.status).toBe(422);
  const problem = await response.json();
  expect(problem.errors).toEqual([
    { path: 'sort', code: 'invalid_value', message: 'Invalid value' },
  ]);
  expect(problem.requestId).toBe(response.headers.get('x-request-id'));
});

it.each(['__proto__=untrusted', '__proto__=one&__proto__=two'])(
  'preserves special query keys so strict schemas reject them: %s',
  async (query) => {
    const schema = z.object({ sort: z.enum(['asc', 'desc']) }).strict();
    const handler = withApiRoute((request, context) =>
      createSuccessResponse(context, validateQuery(schema, new URL(request.url).searchParams)),
    );
    const response = await handler(new Request(`http://localhost/check?sort=asc&${query}`));
    expect(response.status).toBe(422);
    const problem = await response.json();
    expect(problem.errors).toEqual([
      { path: '__proto__', code: 'invalid_value', message: 'Invalid value' },
    ]);
    expect(problem.requestId).toBe(response.headers.get('x-request-id'));
  },
);
