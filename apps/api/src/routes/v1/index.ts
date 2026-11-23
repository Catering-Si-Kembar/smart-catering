import { Router } from 'express';
import { createHealthRouter } from '../health.js';

export function createV1Router(): Router {
  const router = Router();

  router.use('/health', createHealthRouter());

  return router;
}
