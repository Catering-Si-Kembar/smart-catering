import { Router } from 'express';
import {
  JSON_CONTENT_TYPE,
  REQUEST_ID_HEADER,
  createMethodNotAllowedError,
  docsSecurityMiddleware,
  generateOpenApiDocument,
  renderScalarDocsHtml,
  resolveRequestContext,
  type DocsEnvironment,
} from '../lib/index.js';

export function createDocsRouter(envOverride?: DocsEnvironment): Router {
  const router = Router();
  const docsSecurity = docsSecurityMiddleware(envOverride);

  router
    .route('/api/openapi')
    .all(docsSecurity)
    .get((req, res) => {
      const context = resolveRequestContext(req);
      const document = generateOpenApiDocument();
      res.status(200);
      res.setHeader('Content-Type', JSON_CONTENT_TYPE);
      res.setHeader(REQUEST_ID_HEADER, context.requestId);
      res.send(JSON.stringify(document));
    })
    .head((req, res) => {
      const context = resolveRequestContext(req);
      res.status(200);
      res.setHeader('Content-Type', JSON_CONTENT_TYPE);
      res.setHeader(REQUEST_ID_HEADER, context.requestId);
      res.end();
    })
    .all((_req, _res, next) => {
      next(createMethodNotAllowedError(['GET', 'HEAD']));
    });

  router
    .route('/docs')
    .all(docsSecurity)
    .get((req, res) => {
      const context = resolveRequestContext(req);
      const html = renderScalarDocsHtml();
      res.status(200);
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.setHeader(REQUEST_ID_HEADER, context.requestId);
      res.send(html);
    })
    .head((req, res) => {
      const context = resolveRequestContext(req);
      res.status(200);
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.setHeader(REQUEST_ID_HEADER, context.requestId);
      res.end();
    })
    .all((_req, _res, next) => {
      next(createMethodNotAllowedError(['GET', 'HEAD']));
    });

  return router;
}
