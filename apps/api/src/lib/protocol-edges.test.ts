import { afterEach, describe, expect, it, vi } from 'vitest';
import express, { type Express } from 'express';
import type { Server } from 'node:http';
import {
  parsePaginationQuery,
  parseStrictSafeInteger,
  sendNoContent,
  sendSuccess,
  handleApiError,
  evaluateDocsAccess,
  parseBasicAuthHeader,
  docsMethodNotAllowedHandler,
} from './index.js';
import { createDocsRouter } from '../routes/docs.js';

let activeServer: Server | undefined;

afterEach(async () => {
  vi.unstubAllEnvs();
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

describe('protocol edges and strict validations', () => {
  it.each(['9'.repeat(4301), '١', '1\n', '1&page=2'])(
    'rejects unsafe or ambiguous page input with a sanitized 422: %s',
    async (page) => {
      const query =
        page === '1&page=2' ? 'page=1&page=2' : new URLSearchParams({ page }).toString();
      const app = express();
      app.get('/example', (req, res, next) => {
        try {
          const pagination = parsePaginationQuery(req);
          sendSuccess(res, pagination);
        } catch (error) {
          next(error);
        }
      });
      app.use(
        (err: unknown, req: express.Request, res: express.Response, next: express.NextFunction) => {
          handleApiError(err, req, res, next);
        },
      );

      const { origin } = await startApp(app);
      const response = await fetch(`${origin}/example?${query}`);
      expect(response.status).toBe(422);
      expect(response.headers.get('content-type')).toContain('application/problem+json');
      const problem = (await response.json()) as {
        status: number;
        errors: Array<{ path: string; code: string; message: string }>;
        requestId: string;
      };
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
      const env = {
        NODE_ENV: 'production',
        DOCS_ENABLED: 'true',
        DOCS_USERNAME: configured,
        DOCS_PASSWORD: password,
      };

      const app = express();
      app.use(createDocsRouter(env));
      app.use(
        (err: unknown, req: express.Request, res: express.Response, next: express.NextFunction) => {
          handleApiError(err, req, res, next);
        },
      );

      const { origin } = await startApp(app);
      const response = await fetch(`${origin}/api/openapi`, {
        headers: {
          authorization: `Basic ${Buffer.from(`${supplied}:${password}`).toString('base64')}`,
        },
      });

      expect(response.status).toBe(status);
      const body = (await response.json()) as {
        openapi?: string;
        status?: number;
        requestId?: string;
      };
      if (status === 200) {
        expect(body.openapi).toBe('3.1.0');
      } else {
        expect(body.status).toBe(401);
        expect(body.requestId).toBe(response.headers.get('x-request-id'));
      }
    },
  );

  it('does not advertise a body or content type for 204 even with caller-supplied entity headers', async () => {
    const app = express();
    app.get('/example', (_req, res) => {
      sendNoContent(res, {
        headers: { 'Content-Type': 'application/json', 'Content-Length': '123' },
      });
    });

    const { origin } = await startApp(app);
    const response = await fetch(`${origin}/example`);
    expect(response.status).toBe(204);
    expect(await response.text()).toBe('');
    expect(response.headers.has('content-type')).toBe(false);
    expect(response.headers.has('content-length')).toBe(false);
  });

  it('handles parseStrictSafeInteger edge cases strictly', () => {
    expect(parseStrictSafeInteger(-0)).toBeNull();
    expect(parseStrictSafeInteger(3.14)).toBeNull();
    expect(parseStrictSafeInteger(-5)).toBeNull();
    expect(parseStrictSafeInteger(NaN)).toBeNull();
    expect(parseStrictSafeInteger(Infinity)).toBeNull();
    expect(parseStrictSafeInteger(true)).toBeNull();
    expect(parseStrictSafeInteger(false)).toBeNull();
    expect(parseStrictSafeInteger('0x12')).toBeNull();
    expect(parseStrictSafeInteger('1e5')).toBeNull();
    expect(parseStrictSafeInteger(' 10 ')).toBeNull();
    expect(parseStrictSafeInteger('10')).toBe(10);
    expect(parseStrictSafeInteger(0)).toBe(0);
    expect(parseStrictSafeInteger(100)).toBe(100);
  });

  it('handles docs-security environment edge cases', () => {
    expect(() => evaluateDocsAccess({}, { NODE_ENV: 'staging' })).toThrow();
    expect(() =>
      evaluateDocsAccess({}, { NODE_ENV: 'development', DOCS_ENABLED: 'invalid' }),
    ).toThrow();
    expect(() =>
      evaluateDocsAccess(
        {},
        {
          NODE_ENV: 'production',
          DOCS_ENABLED: 'true',
          DOCS_USERNAME: 'user:invalid',
          DOCS_PASSWORD: 'a'.repeat(32),
        },
      ),
    ).toThrow();
    expect(() =>
      evaluateDocsAccess(
        {},
        {
          NODE_ENV: 'production',
          DOCS_ENABLED: 'true',
          DOCS_USERNAME: 'user\nname',
          DOCS_PASSWORD: 'a'.repeat(32),
        },
      ),
    ).toThrow();
    expect(() =>
      evaluateDocsAccess(
        {},
        {
          NODE_ENV: 'production',
          DOCS_ENABLED: 'true',
          DOCS_USERNAME: 'user',
          DOCS_PASSWORD: 'a\n'.repeat(16),
        },
      ),
    ).toThrow();
    expect(() =>
      evaluateDocsAccess(
        {},
        {
          NODE_ENV: 'production',
          DOCS_ENABLED: 'true',
          DOCS_USERNAME: 'user',
          DOCS_PASSWORD: 'short',
        },
      ),
    ).toThrow();
  });

  it('handles parseBasicAuthHeader parsing edges', () => {
    expect(parseBasicAuthHeader(null)).toBeNull();
    expect(parseBasicAuthHeader('Bearer token')).toBeNull();
    expect(parseBasicAuthHeader('Basic not-base-64!')).toBeNull();
    expect(parseBasicAuthHeader('Basic ' + Buffer.from('nocolon').toString('base64'))).toBeNull();
    expect(
      parseBasicAuthHeader('Basic ' + Buffer.from('user\n:pass').toString('base64')),
    ).toBeNull();
  });

  it('provides docsMethodNotAllowedHandler for express routes', async () => {
    const app = express();
    app.all('/docs-method', docsMethodNotAllowedHandler());
    app.use(
      (err: unknown, req: express.Request, res: express.Response, next: express.NextFunction) => {
        handleApiError(err, req, res, next);
      },
    );

    const { origin } = await startApp(app);
    const res = await fetch(`${origin}/docs-method`, { method: 'POST' });
    expect(res.status).toBe(405);
    expect(res.headers.get('allow')).toBe('GET, HEAD');
    expect(res.headers.get('cache-control')).toBe('private, no-store');
    expect(res.headers.get('vary')).toBe('Authorization');
  });
});
