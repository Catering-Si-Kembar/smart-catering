import { Router } from 'express';
import type { HealthData } from '@smart-catering/types';
import { createMethodNotAllowedError } from '../lib/errors.js';
import { sendSuccess } from '../lib/responses.js';

const HEALTH_DATA: HealthData<'api'> = Object.freeze({
  status: 'ok',
  service: 'api',
});

export function createHealthRouter(): Router {
  const router = Router();

  router
    .route('/')
    .get((_req, res) => {
      sendSuccess(res, HEALTH_DATA);
    })
    .head((_req, res) => {
      sendSuccess(res, HEALTH_DATA);
    })
    .all((_req, _res, next) => {
      next(createMethodNotAllowedError(['GET', 'HEAD']));
    });

  return router;
}
