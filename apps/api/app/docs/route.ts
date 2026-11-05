import { ApiReference } from '@scalar/nextjs-api-reference';
import {
  DOCS_SECURITY_HEADERS,
  buildScalarConfiguration,
  createDocsMethodNotAllowedHandler,
  withDocsSecurity,
} from '../../lib/index';

export const dynamic = 'force-dynamic';

const renderScalarReference = ApiReference(() => buildScalarConfiguration(), {
  headers: DOCS_SECURITY_HEADERS,
});

const handleGetOrHead = withDocsSecurity(async (request) => {
  return renderScalarReference(request);
});

export const GET = handleGetOrHead;
export const HEAD = handleGetOrHead;

const methodNotAllowed = createDocsMethodNotAllowedHandler();

export const POST = methodNotAllowed;
export const PUT = methodNotAllowed;
export const PATCH = methodNotAllowed;
export const DELETE = methodNotAllowed;
export const OPTIONS = methodNotAllowed;
