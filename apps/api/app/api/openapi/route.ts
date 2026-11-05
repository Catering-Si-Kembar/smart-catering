import { NextResponse } from 'next/server';
import {
  DOCS_SECURITY_HEADERS,
  JSON_CONTENT_TYPE,
  REQUEST_ID_HEADER,
  createDocsMethodNotAllowedHandler,
  generateOpenApiDocument,
  withDocsSecurity,
} from '../../../lib/index';

export const dynamic = 'force-dynamic';

const handleGetOrHead = withDocsSecurity((_request, context) => {
  const document = generateOpenApiDocument();
  return new NextResponse(JSON.stringify(document), {
    status: 200,
    headers: {
      ...DOCS_SECURITY_HEADERS,
      'Content-Type': JSON_CONTENT_TYPE,
      [REQUEST_ID_HEADER]: context.requestId,
    },
  });
});

export const GET = handleGetOrHead;
export const HEAD = handleGetOrHead;

const methodNotAllowed = createDocsMethodNotAllowedHandler();

export const POST = methodNotAllowed;
export const PUT = methodNotAllowed;
export const PATCH = methodNotAllowed;
export const DELETE = methodNotAllowed;
export const OPTIONS = methodNotAllowed;
