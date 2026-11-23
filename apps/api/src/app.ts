import express, { type Express } from 'express';
import helmet from 'helmet';
import cors from 'cors';
import {
  REQUEST_ID_HEADER,
  createBadRequestError,
  createNotFoundError,
  handleApiError,
  resolveRequestContext,
  type DocsEnvironment,
} from './lib/index.js';
import { createHealthRouter } from './routes/health.js';
import { createDocsRouter } from './routes/docs.js';
import { createV1Router } from './routes/v1/index.js';

export function createApiApp(envOverride?: DocsEnvironment): Express {
  const app = express();

  app.disable('x-powered-by');

  app.use((req, res, next) => {
    const context = resolveRequestContext(req);
    res.setHeader(REQUEST_ID_HEADER, context.requestId);
    next();
  });

  app.use(helmet({ contentSecurityPolicy: false }));
  app.use(cors({ origin: false }));

  app.use(
    express.json({
      limit: '1mb',
      strict: false,
      verify: (_req, _res, buf) => {
        if (buf.length === 0 || buf.toString('utf8').trim().length === 0) {
          throw createBadRequestError('The request body contains malformed JSON.');
        }
      },
    }),
  );

  app.use('/health', createHealthRouter());
  app.use(createDocsRouter(envOverride));
  app.use('/api/v1', createV1Router());

  app.use((_req, _res, next) => {
    next(createNotFoundError('The requested resource was not found.'));
  });

  app.use(
    (err: unknown, req: express.Request, res: express.Response, next: express.NextFunction) => {
      handleApiError(err, req, res, next);
    },
  );

  return app;
}

export default createApiApp;
