import type { Server } from 'node:http';
import express, { type Express } from 'express';
import { afterEach, describe, expect, it } from 'vitest';
import Joi from 'joi';
import {
  ApiHttpError,
  CANONICAL_UUID_REGEX,
  buildProblemDetails,
  createBadRequestError,
  createForbiddenError,
  createInternalServerError,
  createMethodNotAllowedError,
  createNotFoundError,
  createPaginationMeta,
  createSuccessEnvelope,
  createUnauthorizedError,
  createValidationError,
  extractInstancePath,
  handleApiError,
  isProblemStatus,
  isRequestContext,
  isValidRequestId,
  normalizeProblemStatus,
  normalizeRequestId,
  parseAndValidateJsonBody,
  parseJsonBody,
  parsePaginationQuery,
  parseStrictSafeInteger,
  resolveRequestContext,
  sendCreated,
  sendNoContent,
  sendPaginated,
  sendProblemResponse,
  sendSuccess,
  validatePayload,
  validateQuery,
} from './index.js';

let activeServer: Server | undefined;

afterEach(async () => {
  if (activeServer) {
    await new Promise<void>((resolveClose) => activeServer!.close(() => resolveClose()));
    activeServer = undefined;
  }
});

async function startApp(app: Express): Promise<{ port: number; origin: string }> {
  return new Promise((resolveListening) => {
    activeServer = app.listen(0, '127.0.0.1', () => {
      const address = activeServer!.address();
      const port = typeof address === 'object' && address ? address.port : 0;
      resolveListening({ port, origin: `http://127.0.0.1:${port}` });
    });
  });
}

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

  it('checks isValidRequestId with non-string and invalid lengths', () => {
    expect(isValidRequestId(12345)).toBe(false);
    expect(isValidRequestId(null)).toBe(false);
    expect(isValidRequestId('too-short')).toBe(false);
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
    expect(extractInstancePath(new URL('http://127.0.0.1:3001/health'))).toBe('/health');
    expect(extractInstancePath('http://127.0.0.1:3001/health?foo=bar#hash')).toBe('/health');
    expect(extractInstancePath('/orders/123?foo=bar#hash')).toBe('/orders/123');
    expect(extractInstancePath('relative/path')).toBe('/relative/path');
    expect(extractInstancePath('?onlyQuery')).toBe('/');
    expect(extractInstancePath('#onlyHash')).toBe('/');
  });

  it('handles isRequestContext validation', () => {
    expect(isRequestContext(null)).toBe(false);
    expect(isRequestContext('string')).toBe(false);
    expect(isRequestContext({})).toBe(false);
    expect(isRequestContext({ requestId: 'abc', instance: '/test' })).toBe(true);
    expect(resolveRequestContext({ requestId: 'abc', instance: '/test' })).toEqual({
      requestId: 'abc',
      instance: '/test',
    });
  });

  it('resolves request context from custom objects and headers', () => {
    const fromHeaders = resolveRequestContext({
      headers: { 'x-request-id': 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b' },
      url: '/from-headers?foo=bar',
    });
    expect(fromHeaders.requestId).toBe('b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b');
    expect(fromHeaders.instance).toBe('/from-headers');

    const fromGetter = resolveRequestContext({
      get: (h: string) =>
        h === 'x-request-id' ? 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b' : undefined,
      originalUrl: '/from-getter',
    });
    expect(fromGetter.requestId).toBe('b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b');
    expect(fromGetter.instance).toBe('/from-getter');
  });
});

describe('response envelope and 204 helpers', () => {
  it('wraps 200 and 201 payloads in { data, meta: { requestId } } with X-Request-Id header', async () => {
    const requestId = 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b';
    const app = express();

    app.get('/test-200', (_req, res) => {
      sendSuccess(res, { status: 'ok', service: 'api' });
    });
    app.post('/test-201', (_req, res) => {
      sendCreated(res, { id: 'order_123' }, { location: '/orders/order_123' });
    });
    app.post('/test-201-no-loc', (_req, res) => {
      sendCreated(res, { id: 'order_456' });
    });

    const { origin } = await startApp(app);

    const okResponse = await fetch(`${origin}/test-200`, {
      headers: { 'x-request-id': requestId.toUpperCase() },
    });
    expect(okResponse.status).toBe(200);
    expect(okResponse.headers.get('x-request-id')).toBe(requestId);
    expect(okResponse.headers.get('cache-control')).toBe('no-store');
    expect(okResponse.headers.get('content-type')).toContain('application/json');

    const okBody = (await okResponse.json()) as Record<string, unknown>;
    expect(okBody).toEqual({
      data: { status: 'ok', service: 'api' },
      meta: { requestId },
    });

    const createdResponse = await fetch(`${origin}/test-201`, {
      method: 'POST',
      headers: { 'x-request-id': requestId },
    });
    expect(createdResponse.status).toBe(201);
    expect(createdResponse.headers.get('location')).toBe('/orders/order_123');
    expect(createdResponse.headers.get('x-request-id')).toBe(requestId);

    const noLocResponse = await fetch(`${origin}/test-201-no-loc`, { method: 'POST' });
    expect(noLocResponse.status).toBe(201);
    expect(noLocResponse.headers.has('location')).toBe(false);
  });

  it('supports HEAD method with empty body on sendSuccess', async () => {
    const app = express();
    app.all('/test-head', (_req, res) => {
      sendSuccess(res, { data: 'test' });
    });

    const { origin } = await startApp(app);
    const headResponse = await fetch(`${origin}/test-head`, { method: 'HEAD' });
    expect(headResponse.status).toBe(200);
    expect(await headResponse.text()).toBe('');
  });

  it('attaches pagination meta and calculates totals on 200 responses', async () => {
    const app = express();
    app.get('/items', (_req, res) => {
      sendPaginated(res, [{ id: 1 }, { id: 2 }], { page: 2, limit: 10, total: 35 });
    });
    app.get('/items-precalculated', (_req, res) => {
      const meta = createPaginationMeta({ page: 1, limit: 20, total: 100 });
      sendPaginated(res, [{ id: 1 }], meta);
    });

    const { origin } = await startApp(app);
    const response = await fetch(`${origin}/items`);
    expect(response.status).toBe(200);

    const body = (await response.json()) as {
      data: unknown[];
      meta: { pagination: { page: number; limit: number; total: number; totalPages: number } };
    };
    expect(body.data).toEqual([{ id: 1 }, { id: 2 }]);
    expect(body.meta.pagination).toEqual({
      page: 2,
      limit: 10,
      total: 35,
      totalPages: 4,
    });

    const precalcRes = await fetch(`${origin}/items-precalculated`);
    expect(precalcRes.status).toBe(200);
  });

  it('handles 204 No Content without body, Content-Type, or Content-Length', async () => {
    const app = express();
    app.delete('/items/1', (_req, res) => {
      sendNoContent(res, {
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': '123',
          'X-Custom': 'Value',
        },
      });
    });

    const { origin } = await startApp(app);
    const response = await fetch(`${origin}/items/1`, { method: 'DELETE' });

    expect(response.status).toBe(204);
    expect(await response.text()).toBe('');
    expect(response.headers.has('content-type')).toBe(false);
    expect(response.headers.has('content-length')).toBe(false);
    expect(response.headers.get('cache-control')).toBe('no-store');
    expect(response.headers.get('x-custom')).toBe('Value');
  });

  it('tests createSuccessEnvelope directly with different request inputs', () => {
    const envelope1 = createSuccessEnvelope({ item: 1 }, 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b');
    expect(envelope1.meta.requestId).toBe('b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b');

    const envelope2 = createSuccessEnvelope({ item: 2 }, { requestId: 'custom', instance: '/' });
    expect(envelope2.meta.requestId).toBe('custom');

    const envelope3 = createSuccessEnvelope({ item: 3 }, undefined);
    expect(envelope3.meta.requestId).toMatch(CANONICAL_UUID_REGEX);
  });
});

describe('pagination parsing and validation', () => {
  it('parses valid numeric and decimal digit string pagination values', () => {
    expect(parseStrictSafeInteger(42)).toBe(42);
    const fromStrings = parsePaginationQuery(new URLSearchParams({ page: '3', limit: '50' }));
    expect(fromStrings).toEqual({ page: 3, limit: 50, offset: 100 });

    const fromNumbers = parsePaginationQuery({ page: 1, limit: 20 });
    expect(fromNumbers).toEqual({ page: 1, limit: 20, offset: 0 });

    const defaults = parsePaginationQuery(new URLSearchParams());
    expect(defaults).toEqual({ page: 1, limit: 20, offset: 0 });

    const fromUrl = parsePaginationQuery(new URL('http://127.0.0.1/items?page=2&limit=10'));
    expect(fromUrl).toEqual({ page: 2, limit: 10, offset: 10 });
  });

  it('rejects invalid or out of range pagination with 422', () => {
    expect(() => parsePaginationQuery({ page: 0, limit: 20 })).toThrow(ApiHttpError);
    expect(() => parsePaginationQuery({ page: 1, limit: 101 })).toThrow(ApiHttpError);
    expect(() => parsePaginationQuery({ page: 'abc', limit: 20 })).toThrow(ApiHttpError);
    expect(() => parsePaginationQuery(null as unknown as object)).toThrow(ApiHttpError);
    expect(() => parsePaginationQuery([] as unknown as object)).toThrow(ApiHttpError);
  });

  it('creates pagination meta and handles zero items edge case', () => {
    const zeroMeta = createPaginationMeta({ page: 1, limit: 20, total: 0 });
    expect(zeroMeta).toEqual({ page: 1, limit: 20, total: 0, totalPages: 0 });

    const normalMeta = createPaginationMeta({ page: 3, limit: 15, total: 40 });
    expect(normalMeta).toEqual({ page: 3, limit: 15, total: 40, totalPages: 3 });

    expect(() => createPaginationMeta({ page: 1, limit: 20, total: -1 })).toThrow(ApiHttpError);
    expect(() => createPaginationMeta(null as unknown as object)).toThrow(ApiHttpError);
  });
});

describe('errors and problem details', () => {
  it('creates sanitized ProblemDetails objects', () => {
    const problem = buildProblemDetails({
      status: 404,
      instance: '/items/99',
      requestId: 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b',
    });

    expect(problem).toEqual({
      type: 'about:blank',
      title: 'Not Found',
      status: 404,
      detail: 'The requested resource was not found.',
      instance: '/items/99',
      requestId: 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b',
    });
  });

  it('normalizes status codes and problem checks', () => {
    expect(isProblemStatus(200)).toBe(false);
    expect(isProblemStatus(404)).toBe(true);
    expect(normalizeProblemStatus(200)).toBe(500);
    expect(normalizeProblemStatus(404)).toBe(404);
  });

  it('provides all standard error factory helpers', () => {
    expect(createBadRequestError().status).toBe(400);
    expect(createUnauthorizedError().status).toBe(401);
    expect(createForbiddenError().status).toBe(403);
    expect(createNotFoundError().status).toBe(404);
    const notAllowed = createMethodNotAllowedError(['GET', 'HEAD']);
    expect(notAllowed.status).toBe(405);
    expect(notAllowed.headers?.['Allow']).toBe('GET, HEAD');
    expect(
      createValidationError([{ path: 'name', code: 'invalid_value', message: 'Invalid value' }])
        .status,
    ).toBe(422);
    expect(createInternalServerError().status).toBe(500);

    const errWithHeaders = createUnauthorizedError('details', { 'X-Auth': 'required' });
    expect(errWithHeaders.headers?.['X-Auth']).toBe('required');
  });

  it('supports HEAD method for sendProblemResponse and handles headersSent in handleApiError', async () => {
    const app = express();
    app.all('/problem-head', (_req, res) => {
      sendProblemResponse(
        res,
        buildProblemDetails({
          status: 404,
          instance: '/problem-head',
          requestId: 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b',
        }),
      );
    });
    app.get('/headers-sent', (_req, res, next) => {
      res.writeHead(200);
      res.write('ok');
      res.end();
      handleApiError(new Error('after-sent'), _req, res, next);
    });

    const { origin } = await startApp(app);
    const headRes = await fetch(`${origin}/problem-head`, { method: 'HEAD' });
    expect(headRes.status).toBe(404);
    expect(await headRes.text()).toBe('');

    const sentRes = await fetch(`${origin}/headers-sent`);
    expect(sentRes.status).toBe(200);
  });
});

describe('Joi validation helpers', () => {
  const schema = Joi.object({
    name: Joi.string().required(),
    count: Joi.number().integer().min(1).required(),
  }).strict();

  it('validates valid payloads and returns typed data', () => {
    const data = validatePayload(schema, { name: 'catering', count: 10 });
    expect(data).toEqual({ name: 'catering', count: 10 });
  });

  it('rejects unknown properties in strict mode', () => {
    expect(() => validatePayload(schema, { name: 'catering', count: 10, extra: true })).toThrow(
      ApiHttpError,
    );
  });

  it('validates query strings from various sources', () => {
    const querySchema = Joi.object({
      category: Joi.string().valid('lunch', 'dinner').required(),
    }).strict();

    expect(validateQuery(querySchema, 'http://127.0.0.1/menus?category=lunch')).toEqual({
      category: 'lunch',
    });
    expect(validateQuery(querySchema, new URL('http://127.0.0.1/menus?category=lunch'))).toEqual({
      category: 'lunch',
    });
    expect(validateQuery(querySchema, new URLSearchParams({ category: 'lunch' }))).toEqual({
      category: 'lunch',
    });
    expect(validateQuery(querySchema, { category: 'lunch' })).toEqual({ category: 'lunch' });
    expect(
      validateQuery(querySchema, new Request('http://127.0.0.1/menus?category=lunch')),
    ).toEqual({ category: 'lunch' });

    expect(() => validateQuery(querySchema, 'http://127.0.0.1/menus?category=breakfast')).toThrow(
      ApiHttpError,
    );
  });

  it('parses JSON bodies with parseJsonBody and parseAndValidateJsonBody', async () => {
    const validJson = JSON.stringify({ name: 'box', count: 5 });
    const parsed = await parseJsonBody(validJson);
    expect(parsed).toEqual({ name: 'box', count: 5 });

    const validated = await parseAndValidateJsonBody(validJson, schema);
    expect(validated).toEqual({ name: 'box', count: 5 });

    await expect(parseJsonBody('')).rejects.toThrow(ApiHttpError);
    await expect(parseJsonBody('invalid-json')).rejects.toThrow(ApiHttpError);

    const webReq = new Request('http://127.0.0.1', { method: 'POST', body: validJson });
    expect(await parseJsonBody(webReq)).toEqual({ name: 'box', count: 5 });

    const webReqEmpty = new Request('http://127.0.0.1', { method: 'POST', body: '' });
    await expect(parseJsonBody(webReqEmpty)).rejects.toThrow(ApiHttpError);

    const expressMock = { body: { name: 'box', count: 5 } } as unknown as express.Request;
    expect(await parseJsonBody(expressMock)).toEqual({ name: 'box', count: 5 });

    const expressNullMock = { body: null } as unknown as express.Request;
    await expect(parseJsonBody(expressNullMock)).rejects.toThrow(ApiHttpError);

    const expressBlankMock = { body: '   ' } as unknown as express.Request;
    await expect(parseJsonBody(expressBlankMock)).rejects.toThrow(ApiHttpError);

    const expressUndefMock = {} as unknown as express.Request;
    await expect(parseJsonBody(expressUndefMock)).rejects.toThrow(ApiHttpError);
  });
});
