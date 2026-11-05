import { describe, expect, it } from 'vitest';
import { z } from 'zod';
import {
  CANONICAL_UUID_REGEX,
  extractInstancePath,
  isValidRequestId,
  normalizeRequestId,
  resolveRequestContext,
} from './request-context';
import {
  ApiHttpError,
  createBadRequestError,
  createForbiddenError,
  createInternalServerError,
  createMethodNotAllowedError,
  createNotFoundError,
  createProblemResponse,
  createUnauthorizedError,
  createValidationError,
  handleApiError,
} from './errors';
import { parseAndValidateJsonBody, validatePayload, validateQuery } from './validation';
import { formatZodIssues } from './validation-issues';
import { MAX_SAFE_PAGINATION_INT, createPaginationMeta, parsePaginationQuery } from './pagination';
import {
  createCreatedResponse,
  createNoContentResponse,
  createPaginatedResponse,
  createSuccessResponse,
} from './responses';
import { withApiRoute } from './route-handler';

describe('request-context helpers', () => {
  it.each([
    'b4b3cfc5-5a7e-1d0a-8c6f-740078c5158b',
    'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b',
    '0192f0c0-1234-7abc-acde-1234567890ab',
    'B4B3CFC5-5A7E-8D0A-BC6F-740078C5158B',
  ])('preserves and lowercases valid canonical UUID %s (versions 1-8, RFC variant)', (incoming) => {
    const normalized = normalizeRequestId(incoming);
    expect(normalized).toBe(incoming.toLowerCase());
    expect(isValidRequestId(normalized)).toBe(true);
  });

  it.each([
    undefined,
    null,
    '',
    '   ',
    'not-a-uuid',
    'b4b3cfc5-5a7e-0d0a-9c6f-740078c5158b',
    'b4b3cfc5-5a7e-9d0a-9c6f-740078c5158b',
    'b4b3cfc5-5a7e-4d0a-1c6f-740078c5158b',
    'b4b3cfc5-5a7e-4d0a-fc6f-740078c5158b',
    'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b-extra',
    'x'.repeat(200),
  ])('generates a fresh lowercase UUIDv4 when x-request-id is invalid or oversize (%j)', (raw) => {
    const generated = normalizeRequestId(raw);
    expect(generated).toMatch(CANONICAL_UUID_REGEX);
    expect(generated).toBe(generated.toLowerCase());
  });

  it('caches a single RequestContext per Request instance and strips query strings from instance', () => {
    const request = new Request('http://127.0.0.1:3001/orders/123?secret=token&page=2', {
      headers: { 'x-request-id': 'not-valid-uuid' },
    });

    const first = resolveRequestContext(request);
    const second = resolveRequestContext(request);

    expect(first).toBe(second);
    expect(first.requestId).toBe(second.requestId);
    expect(first.instance).toBe('/orders/123');
    expect(extractInstancePath('http://127.0.0.1:3001/health?foo=bar#hash')).toBe('/health');
  });
});

describe('response envelope and 204 helpers', () => {
  it('wraps 200 and 201 payloads in { data, meta: { requestId } } with X-Request-Id header', async () => {
    const requestId = 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b';
    const request = new Request('http://127.0.0.1:3001/health', {
      headers: { 'x-request-id': requestId.toUpperCase() },
    });

    const okResponse = createSuccessResponse(request, { status: 'ok', service: 'api' });
    expect(okResponse.status).toBe(200);
    expect(okResponse.headers.get('x-request-id')).toBe(requestId);
    expect(okResponse.headers.get('cache-control')).toBe('no-store');
    expect(okResponse.headers.get('content-type')).toContain('application/json');

    const okBody = (await okResponse.json()) as Record<string, unknown>;
    expect(okBody).toEqual({
      data: { status: 'ok', service: 'api' },
      meta: { requestId },
    });
    expect(okBody).not.toHaveProperty('success');
    expect(okBody).not.toHaveProperty('error');

    const createdResponse = createCreatedResponse(
      request,
      { id: 'ord_1' },
      { location: '/orders/ord_1' },
    );
    expect(createdResponse.status).toBe(201);
    expect(createdResponse.headers.get('location')).toBe('/orders/ord_1');
    expect(createdResponse.headers.get('x-request-id')).toBe(requestId);
    expect(await createdResponse.json()).toEqual({
      data: { id: 'ord_1' },
      meta: { requestId },
    });
  });

  it('includes meta.pagination on paginated success responses', async () => {
    const request = new Request('http://127.0.0.1:3001/items', {
      headers: { 'x-request-id': 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b' },
    });
    const response = createPaginatedResponse(request, ['a', 'b'], {
      page: 2,
      limit: 10,
      total: 25,
    });

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      data: ['a', 'b'],
      meta: {
        requestId: 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b',
        pagination: {
          page: 2,
          limit: 10,
          total: 25,
          totalPages: 3,
        },
      },
    });
  });

  it('returns an empty body and no JSON content-type for 204 responses while keeping X-Request-Id', async () => {
    const request = new Request('http://127.0.0.1:3001/resource', {
      method: 'DELETE',
      headers: { 'x-request-id': 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b' },
    });

    const response = createNoContentResponse(request);
    expect(response.status).toBe(204);
    expect(response.headers.get('x-request-id')).toBe('b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b');
    expect(response.headers.get('content-type')).toBeNull();
    expect(await response.text()).toBe('');
  });
});

describe('RFC 9457 problem details and error sanitization', () => {
  it('maps 400, 401, 403, 404, 405, 422, and 500 with exact titles and application/problem+json', async () => {
    const request = new Request('http://127.0.0.1:3001/orders?apiKey=secret123', {
      headers: { 'x-request-id': 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b' },
    });

    const cases: ReadonlyArray<{ error: ApiHttpError; status: number; title: string }> = [
      { error: createBadRequestError(), status: 400, title: 'Bad Request' },
      { error: createUnauthorizedError(), status: 401, title: 'Unauthorized' },
      { error: createForbiddenError(), status: 403, title: 'Forbidden' },
      { error: createNotFoundError(), status: 404, title: 'Not Found' },
      {
        error: createMethodNotAllowedError(['GET', 'HEAD']),
        status: 405,
        title: 'Method Not Allowed',
      },
      {
        error: createValidationError([
          { path: 'quantity', code: 'invalid_value', message: 'Invalid value' },
        ]),
        status: 422,
        title: 'Unprocessable Content',
      },
      { error: createInternalServerError(), status: 500, title: 'Internal Server Error' },
    ];

    for (const testCase of cases) {
      const response = handleApiError(testCase.error, request);
      expect(response.status).toBe(testCase.status);
      expect(response.headers.get('content-type')).toContain('application/problem+json');
      expect(response.headers.get('x-request-id')).toBe('b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b');

      const body = (await response.json()) as Record<string, unknown>;
      expect(body.type).toBe('about:blank');
      expect(body.title).toBe(testCase.title);
      expect(body.status).toBe(testCase.status);
      expect(body.instance).toBe('/orders');
      expect(body.requestId).toBe('b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b');
    }
  });

  it('never leaks SQL, exception text, stack traces, or env secrets on unexpected 500 errors', async () => {
    const request = new Request('http://127.0.0.1:3001/health?password=super-secret-value');
    const sensitiveError = new Error(
      'PrismaClientKnownRequestError: SELECT * FROM users WHERE secret="TOP_SECRET_TOKEN"',
    );

    const response = handleApiError(sensitiveError, request);
    expect(response.status).toBe(500);
    const rawText = await response.text();
    expect(rawText).not.toContain('PrismaClient');
    expect(rawText).not.toContain('SELECT *');
    expect(rawText).not.toContain('TOP_SECRET_TOKEN');
    expect(rawText).not.toContain('super-secret-value');

    const parsed = JSON.parse(rawText) as Record<string, unknown>;
    expect(parsed).toEqual({
      type: 'about:blank',
      title: 'Internal Server Error',
      status: 500,
      detail: 'An unexpected error occurred.',
      instance: '/health',
      requestId: response.headers.get('x-request-id'),
    });

    const explicit500 = createProblemResponse(request, {
      status: 500,
      detail: 'Database connection string postgresql://admin:secret@db:5432 failed',
    });
    expect((await explicit500.json()).detail).toBe('An unexpected error occurred.');
  });
});

describe('Zod validation helpers', () => {
  const OrderSchema = z
    .object({
      customer: z.object({
        name: z.string().min(2),
      }),
      portions: z.number().int().positive(),
    })
    .strict();

  it('returns 400 Bad Request ProblemDetails for malformed JSON bodies without leaking syntax error details', async () => {
    const request = new Request('http://127.0.0.1:3001/orders', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: '{"customer": {"name": "Ani"}, "portions": 10',
    });

    let caughtError: unknown;
    try {
      await parseAndValidateJsonBody(request, OrderSchema);
    } catch (error) {
      caughtError = error;
    }

    expect(caughtError).toBeInstanceOf(ApiHttpError);
    const response = handleApiError(caughtError, request);
    expect(response.status).toBe(400);
    const problem = await response.json();
    expect(problem.title).toBe('Bad Request');
    expect(problem.errors).toBeUndefined();
    expect(JSON.stringify(problem)).not.toContain('Ani');
  });

  it('returns 422 Unprocessable Content with normalized errors[] for invalid payload fields and root values', async () => {
    const request = new Request('http://127.0.0.1:3001/orders', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        customer: { name: 'A' },
        portions: -5,
        unexpectedSecret: 'do-not-reflect-me',
      }),
    });

    let caughtError: unknown;
    try {
      await parseAndValidateJsonBody(request, OrderSchema);
    } catch (error) {
      caughtError = error;
    }

    const response = handleApiError(caughtError, request);
    expect(response.status).toBe(422);
    const problem = await response.json();
    expect(problem.title).toBe('Unprocessable Content');
    expect(problem.errors).toEqual([
      { path: 'customer.name', code: 'invalid_value', message: 'Invalid value' },
      { path: 'portions', code: 'invalid_value', message: 'Invalid value' },
      { path: 'unexpectedSecret', code: 'invalid_value', message: 'Invalid value' },
    ]);
    expect(JSON.stringify(problem)).not.toContain('do-not-reflect-me');

    expect(() => validatePayload(OrderSchema, 'not-an-object')).toThrowError(ApiHttpError);
    try {
      validatePayload(OrderSchema, 'not-an-object');
    } catch (rootError) {
      const rootProblem = await handleApiError(rootError, request).json();
      expect(rootProblem.status).toBe(422);
      expect(rootProblem.errors).toEqual([
        { path: '$', code: 'invalid_value', message: 'Invalid value' },
      ]);
    }
  });

  it('validates query parameters and formats ZodError issues consistently', () => {
    const QuerySchema = z.object({ filter: z.enum(['active', 'archived']) });
    const validReq = new Request('http://127.0.0.1:3001/items?filter=active');
    expect(validateQuery(QuerySchema, validReq)).toEqual({ filter: 'active' });

    const invalidReq = new Request('http://127.0.0.1:3001/items?filter=unknown');
    expect(() => validateQuery(QuerySchema, invalidReq)).toThrowError(ApiHttpError);

    const parsed = QuerySchema.safeParse({ filter: 'bad' });
    expect(parsed.success).toBe(false);
    if (!parsed.success) {
      expect(formatZodIssues(parsed.error)).toEqual([
        { path: 'filter', code: 'invalid_value', message: 'Invalid value' },
      ]);
    }
  });
});

describe('pagination helpers', () => {
  it('applies defaults page=1, limit=20 and computes totalPages=0 when total=0', () => {
    expect(parsePaginationQuery()).toEqual({ page: 1, limit: 20, offset: 0 });
    expect(parsePaginationQuery(new URLSearchParams())).toEqual({
      page: 1,
      limit: 20,
      offset: 0,
    });
    expect(createPaginationMeta({ total: 0 })).toEqual({
      page: 1,
      limit: 20,
      total: 0,
      totalPages: 0,
    });
    expect(createPaginationMeta({ page: '3', limit: '25', total: '51' })).toEqual({
      page: 3,
      limit: 25,
      total: 51,
      totalPages: 3,
    });
    expect(
      createPaginationMeta({
        page: 1,
        limit: 1,
        total: MAX_SAFE_PAGINATION_INT,
      }),
    ).toEqual({
      page: 1,
      limit: 1,
      total: MAX_SAFE_PAGINATION_INT,
      totalPages: MAX_SAFE_PAGINATION_INT,
    });
  });

  it.each([
    { input: { page: 0, total: 10 }, expectedPath: 'page' },
    { input: { page: -1, total: 10 }, expectedPath: 'page' },
    { input: { page: 1.5, total: 10 }, expectedPath: 'page' },
    { input: { page: true, total: 10 }, expectedPath: 'page' },
    { input: { page: false, total: 10 }, expectedPath: 'page' },
    { input: { page: '0x10', total: 10 }, expectedPath: 'page' },
    { input: { page: '1e2', total: 10 }, expectedPath: 'page' },
    { input: { page: '1.0', total: 10 }, expectedPath: 'page' },
    { input: { page: '', total: 10 }, expectedPath: 'page' },
    { input: { page: ' 2 ', total: 10 }, expectedPath: 'page' },
    { input: { page: MAX_SAFE_PAGINATION_INT + 1, total: 10 }, expectedPath: 'page' },
    { input: { page: MAX_SAFE_PAGINATION_INT, limit: 20, total: 10 }, expectedPath: 'page' },
    { input: { limit: 0, total: 10 }, expectedPath: 'limit' },
    { input: { limit: -10, total: 10 }, expectedPath: 'limit' },
    { input: { limit: 101, total: 10 }, expectedPath: 'limit' },
    { input: { limit: 20.5, total: 10 }, expectedPath: 'limit' },
    { input: { limit: true, total: 10 }, expectedPath: 'limit' },
    { input: { limit: '0x14', total: 10 }, expectedPath: 'limit' },
    { input: { limit: '2e1', total: 10 }, expectedPath: 'limit' },
    { input: { total: -1 }, expectedPath: 'total' },
    { input: { total: 3.14 }, expectedPath: 'total' },
    { input: { total: true }, expectedPath: 'total' },
    { input: { total: null }, expectedPath: 'total' },
    { input: { total: '0x10' }, expectedPath: 'total' },
    { input: { total: '1e3' }, expectedPath: 'total' },
    { input: { total: '9007199254740992' }, expectedPath: 'total' },
    { input: { total: Number.NaN }, expectedPath: 'total' },
    { input: { total: Number.POSITIVE_INFINITY }, expectedPath: 'total' },
  ])(
    'rejects invalid pagination input %j with 422 on path $expectedPath',
    ({ input, expectedPath }) => {
      let caught: unknown;
      try {
        createPaginationMeta(input);
      } catch (error) {
        caught = error;
      }

      expect(caught).toBeInstanceOf(ApiHttpError);
      const apiError = caught as ApiHttpError;
      expect(apiError.status).toBe(422);
      expect(apiError.errors).toContainEqual({
        path: expectedPath,
        code: 'invalid_value',
        message: 'Invalid value',
      });
    },
  );
});

describe('withApiRoute wrapper', () => {
  it('Preserves single requestId across success, HEAD, and thrown errors without double-wrapping', async () => {
    const handler = withApiRoute(async (req, ctx) => {
      if (new URL(req.url).searchParams.get('fail') === '1') {
        throw new Error('database crash secret');
      }
      return createSuccessResponse(ctx, { ok: true });
    });

    const getReq = new Request('http://127.0.0.1:3001/test', {
      headers: { 'x-request-id': 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b' },
    });
    const getRes = await handler(getReq);
    expect(getRes.status).toBe(200);
    expect(getRes.headers.get('x-request-id')).toBe('b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b');
    expect(await getRes.json()).toEqual({
      data: { ok: true },
      meta: { requestId: 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b' },
    });

    const headReq = new Request('http://127.0.0.1:3001/test', {
      method: 'HEAD',
      headers: { 'x-request-id': 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b' },
    });
    const headRes = await handler(headReq);
    expect(headRes.status).toBe(200);
    expect(headRes.headers.get('x-request-id')).toBe('b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b');
    expect(await headRes.text()).toBe('');

    const failReq = new Request('http://127.0.0.1:3001/test?fail=1', {
      headers: { 'x-request-id': 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b' },
    });
    const failRes = await handler(failReq);
    expect(failRes.status).toBe(500);
    expect(failRes.headers.get('x-request-id')).toBe('b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b');
    expect(await failRes.json()).toEqual({
      type: 'about:blank',
      title: 'Internal Server Error',
      status: 500,
      detail: 'An unexpected error occurred.',
      instance: '/test',
      requestId: 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b',
    });
  });
});
