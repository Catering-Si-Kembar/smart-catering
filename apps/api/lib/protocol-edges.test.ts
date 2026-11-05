import { afterEach, expect, it, vi } from 'vitest';
import { GET as openApi } from '../app/api/openapi/route';
import { parsePaginationQuery } from './pagination';
import { createNoContentResponse, createSuccessResponse } from './responses';
import { withApiRoute } from './route-handler';

afterEach(() => vi.unstubAllEnvs());

it.each(['9'.repeat(4301), '١', '1\n', '1&page=2'])(
  'rejects unsafe or ambiguous page input with a sanitized 422: %s',
  async (page) => {
    const query = page === '1&page=2' ? 'page=1&page=2' : new URLSearchParams({ page }).toString();
    const handler = withApiRoute((request, context) =>
      createSuccessResponse(context, parsePaginationQuery(request)),
    );
    const response = await handler(new Request(`http://localhost/example?${query}`));
    expect(response.status).toBe(422);
    expect(response.headers.get('content-type')).toContain('application/problem+json');
    const problem = await response.json();
    expect(problem.errors).toEqual([
      { path: 'page', code: 'invalid_value', message: 'Invalid value' },
    ]);
    expect(problem.requestId).toBe(response.headers.get('x-request-id'));
    expect(JSON.stringify(problem)).not.toContain(page);
  },
);

it.each([
  ['\uFEFFops', '\uFEFFops', 200],
  ['ops', '\uFEFFops', 401],
  ['pengelola', 'pengelola', 200],
] as const)(
  'preserves exact UTF-8 credential identity: %s/%s',
  async (configured, supplied, status) => {
    const password = '秘密'.repeat(20);
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('DOCS_ENABLED', 'true');
    vi.stubEnv('DOCS_USERNAME', configured);
    vi.stubEnv('DOCS_PASSWORD', password);
    const response = await openApi(
      new Request('http://localhost/api/openapi', {
        headers: {
          authorization: `Basic ${Buffer.from(`${supplied}:${password}`).toString('base64')}`,
        },
      }),
    );
    expect(response.status).toBe(status);
    const body = await response.json();
    if (status === 200) {
      expect(body.openapi).toBe('3.1.0');
    } else {
      expect(body.status).toBe(401);
      expect(body.requestId).toBe(response.headers.get('x-request-id'));
    }
  },
);

it('does not advertise a body or content type for 204 even with caller-supplied entity headers', async () => {
  const response = createNoContentResponse(new Request('http://localhost/example'), {
    headers: { 'Content-Type': 'application/json', 'Content-Length': '123' },
  });
  expect(response.status).toBe(204);
  expect(await response.text()).toBe('');
  expect(response.headers.has('content-type')).toBe(false);
  expect(response.headers.has('content-length')).toBe(false);
});
