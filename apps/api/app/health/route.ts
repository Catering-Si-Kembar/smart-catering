import type { HealthData } from '@smart-catering/types';
import {
  createMethodNotAllowedHandler,
  createSuccessResponse,
  withApiRoute,
} from '../../lib/index';

export const dynamic = 'force-dynamic';

const HEALTH_DATA: HealthData<'api'> = Object.freeze({
  status: 'ok',
  service: 'api',
});

const handleGetOrHead = withApiRoute(
  (_request, context) => {
    return createSuccessResponse(context, HEALTH_DATA);
  },
  {
    allowedMethods: ['GET', 'HEAD'],
  },
);

export const GET = handleGetOrHead;
export const HEAD = handleGetOrHead;

const methodNotAllowed = createMethodNotAllowedHandler(['GET', 'HEAD']);

export const POST = methodNotAllowed;
export const PUT = methodNotAllowed;
export const PATCH = methodNotAllowed;
export const DELETE = methodNotAllowed;
export const OPTIONS = methodNotAllowed;
