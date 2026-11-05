import { NextResponse } from 'next/server';
import { createMethodNotAllowedError, createNotFoundError, handleApiError } from './errors';
import { REQUEST_ID_HEADER, type RequestContext, resolveRequestContext } from './request-context';

export type ApiRouteHandler = (
  request: Request,
  context: RequestContext,
  routeContext?: unknown,
) => Response | Promise<Response>;

export type WithApiRouteOptions = Readonly<{
  allowedMethods?: readonly string[];
  defaultHeaders?: HeadersInit;
}>;

export function normalizeAllowedMethods(methods: readonly string[]): readonly string[] {
  return Object.freeze(
    Array.from(
      new Set(
        methods.flatMap((method) => {
          const upper = method.trim().toUpperCase();
          return upper === 'GET' ? ['GET', 'HEAD'] : [upper];
        }),
      ),
    ),
  );
}

export function stripBodyForHead(response: Response, requestId: string): NextResponse {
  const headers = new Headers(response.headers);
  headers.set(REQUEST_ID_HEADER, requestId);
  return new NextResponse(null, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

function applyDefaultHeaders(
  response: Response,
  requestId: string,
  defaultHeaders?: HeadersInit,
): Response {
  const headers = new Headers(response.headers);
  if (defaultHeaders !== undefined) {
    const extra = new Headers(defaultHeaders);
    extra.forEach((value, key) => {
      if (!headers.has(key)) {
        headers.set(key, value);
      }
    });
  }
  headers.set(REQUEST_ID_HEADER, requestId);

  if (response.status === 204) {
    headers.delete('content-type');
    headers.delete('content-length');
    return new NextResponse(null, {
      status: 204,
      statusText: response.statusText,
      headers,
    });
  }

  return new NextResponse(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

export function withApiRoute(
  handler: ApiRouteHandler,
  options?: WithApiRouteOptions,
): (request: Request, routeContext?: unknown) => Promise<Response> {
  const allowedMethods =
    options?.allowedMethods !== undefined
      ? normalizeAllowedMethods(options.allowedMethods)
      : undefined;

  return async function wrappedRouteHandler(
    request: Request,
    routeContext?: unknown,
  ): Promise<Response> {
    const context = resolveRequestContext(request);
    const method = (request.method || 'GET').toUpperCase();

    try {
      if (allowedMethods !== undefined && !allowedMethods.includes(method)) {
        throw createMethodNotAllowedError(allowedMethods);
      }

      const rawResponse = await handler(request, context, routeContext);
      const withHeaders = applyDefaultHeaders(
        rawResponse,
        context.requestId,
        options?.defaultHeaders,
      );

      if (method === 'HEAD') {
        return stripBodyForHead(withHeaders, context.requestId);
      }

      return withHeaders;
    } catch (error) {
      const errorResponse = handleApiError(error, context, options?.defaultHeaders);
      if (method === 'HEAD') {
        return stripBodyForHead(errorResponse, context.requestId);
      }
      return errorResponse;
    }
  };
}

export function createMethodNotAllowedHandler(
  allowedMethods: readonly string[],
  defaultHeaders?: HeadersInit,
): (request: Request) => Promise<Response> {
  const normalized = normalizeAllowedMethods(allowedMethods);
  return withApiRoute(
    () => {
      throw createMethodNotAllowedError(normalized);
    },
    defaultHeaders !== undefined ? { defaultHeaders } : undefined,
  );
}

export function createNotFoundHandler(
  defaultHeaders?: HeadersInit,
): (request: Request) => Promise<Response> {
  return withApiRoute(
    () => {
      throw createNotFoundError();
    },
    defaultHeaders !== undefined ? { defaultHeaders } : undefined,
  );
}
