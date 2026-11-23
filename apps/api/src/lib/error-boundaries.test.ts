import type { Server } from 'node:http';
import { format } from 'node:util';
import express, { type Express } from 'express';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Joi from 'joi';
import { handleApiError } from './errors.js';
import { sendSuccess } from './responses.js';
import { validatePayload, validateQuery } from './validation.js';
import { docsSecurityMiddleware } from './docs-security.js';

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

describe('error-boundaries and safety guarantees', () => {
  const payloadSchema = Joi.object({
    settings: Joi.object({
      amount: Joi.number().required(),
    })
      .strict()
      .required(),
  }).strict();

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
    'converts native Joi parsing failures to a sanitized 422: $label',
    async ({ payload, paths }) => {
      const app = express();
      app.use(express.json({ strict: false }));
      app.post('/check', (req, res, next) => {
        try {
          const validated = validatePayload(payloadSchema, req.body);
          sendSuccess(res, validated);
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
      const response = await fetch(`${origin}/check?token=PRIVATE_VALUE`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      expect(response.status).toBe(422);
      expect(response.headers.get('content-type')).toContain('application/problem+json');
      const problem = (await response.json()) as {
        status: number;
        errors: Array<{ path: string; code: string; message: string }>;
        requestId: string;
        instance: string;
      };
      expect(problem.errors.map((issue) => issue.path).sort()).toEqual(paths.sort());
      expect(problem.requestId).toBe(response.headers.get('x-request-id'));
      expect(problem.instance).toBe('/check');
      expect(JSON.stringify(problem)).not.toContain('PRIVATE_VALUE');
    },
  );

  it('classifies an empty JSON request as malformed input rather than schema validation', async () => {
    const app = express();
    app.use(
      express.json({
        verify: (_req, _res, buf) => {
          if (buf.length === 0 || buf.toString('utf8').trim().length === 0) {
            const err = new SyntaxError('The request body contains malformed JSON.');
            (err as unknown as { status: number }).status = 400;
            throw err;
          }
        },
      }),
    );
    app.post('/check', (req, res, next) => {
      try {
        const validated = validatePayload(payloadSchema, req.body);
        sendSuccess(res, validated);
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
    const response = await fetch(`${origin}/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '',
    });

    expect(response.status).toBe(400);
    expect(response.headers.get('content-type')).toContain('application/problem+json');
    const problem = (await response.json()) as { status: number; requestId: string };
    expect(problem.status).toBe(400);
    expect(problem.requestId).toBe(response.headers.get('x-request-id'));
  });

  it('forces private documentation cache policy even when a route supplies public headers', async () => {
    const app = express();
    app.use('/docs', docsSecurityMiddleware({ NODE_ENV: 'test', DOCS_ENABLED: 'true' }));
    app.get('/docs', (_req, res) => {
      res.setHeader('Cache-Control', 'public, max-age=3600');
      res.setHeader('Vary', 'Accept-Encoding');
      res.send('<!doctype html>');
    });

    const { origin } = await startApp(app);
    const response = await fetch(`${origin}/docs`);
    expect(response.status).toBe(200);
    expect(response.headers.get('cache-control')).toBe('private, no-store');
    expect(response.headers.get('vary')).toBe('Authorization');
  });

  it('logs a correlated server failure without exposing exception secrets or query parameters', async () => {
    const capture = vi.spyOn(console, 'error').mockImplementation(() => {});
    try {
      const app = express();
      app.get('/failure', () => {
        throw new Error('SECRET_DATABASE_PASSWORD and private SQL');
      });
      app.use(
        (err: unknown, req: express.Request, res: express.Response, next: express.NextFunction) => {
          handleApiError(err, req, res, next);
        },
      );

      const { origin } = await startApp(app);
      const response = await fetch(`${origin}/failure?token=SECRET_QUERY`);
      expect(response.status).toBe(500);

      const problem = (await response.json()) as {
        status: number;
        detail: string;
        requestId: string;
      };
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
    const querySchema = Joi.object({
      sort: Joi.string().valid('asc', 'desc').required(),
    }).strict();

    const app = express();
    app.get('/check', (req, res, next) => {
      try {
        const query = validateQuery(querySchema, req);
        sendSuccess(res, query);
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
    const response = await fetch(`${origin}/check?sort=asc&sort=desc`);
    expect(response.status).toBe(422);
    const problem = (await response.json()) as {
      status: number;
      errors: Array<{ path: string; code: string; message: string }>;
    };
    expect(problem.errors).toEqual([
      { path: 'sort', code: 'invalid_value', message: 'Invalid value' },
    ]);
  });

  it('rejects __proto__ query key strictly with 422', async () => {
    const querySchema = Joi.object({
      filter: Joi.string().optional(),
    }).strict();

    const app = express();
    app.get('/check', (req, res, next) => {
      try {
        const query = validateQuery(querySchema, req);
        sendSuccess(res, query);
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
    const response = await fetch(`${origin}/check?__proto__=polluted`);
    expect(response.status).toBe(422);
    const problem = (await response.json()) as {
      status: number;
      errors: Array<{ path: string; code: string; message: string }>;
    };
    expect(problem.errors).toEqual([
      { path: '__proto__', code: 'invalid_value', message: 'Invalid value' },
    ]);
  });
});
