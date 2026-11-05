import { NextResponse } from 'next/server';
import type { ApiMeta, ApiSuccess, PaginationMeta } from '@smart-catering/types';
import { type PaginationMetaInput, createPaginationMeta } from './pagination';
import {
  REQUEST_ID_HEADER,
  type RequestContext,
  isRequestContext,
  normalizeRequestId,
  resolveRequestContext,
} from './request-context';

export const JSON_CONTENT_TYPE = 'application/json; charset=utf-8';

function resolveRequestId(requestOrContext: Request | RequestContext | string): string {
  if (typeof requestOrContext === 'string') {
    return normalizeRequestId(requestOrContext);
  }
  if (isRequestContext(requestOrContext)) {
    return requestOrContext.requestId;
  }
  return resolveRequestContext(requestOrContext).requestId;
}

export function createSuccessEnvelope<TData>(
  data: TData,
  requestOrContext: Request | RequestContext | string,
  pagination?: PaginationMeta,
): ApiSuccess<TData> {
  const requestId = resolveRequestId(requestOrContext);
  const meta: ApiMeta =
    pagination !== undefined
      ? Object.freeze({ requestId, pagination })
      : Object.freeze({ requestId });

  return Object.freeze({
    data,
    meta,
  });
}

export type CreateSuccessResponseOptions = Readonly<{
  status?: 200 | 201;
  pagination?: PaginationMeta;
  headers?: HeadersInit;
}>;

export function createSuccessResponse<TData>(
  requestOrContext: Request | RequestContext,
  data: TData,
  options?: CreateSuccessResponseOptions,
): NextResponse<ApiSuccess<TData>> {
  const context = resolveRequestContext(requestOrContext);
  const status = options?.status ?? 200;
  const envelope = createSuccessEnvelope(data, context, options?.pagination);

  const headers = new Headers(options?.headers);
  headers.set('Content-Type', JSON_CONTENT_TYPE);
  if (!headers.has('Cache-Control')) {
    headers.set('Cache-Control', 'no-store');
  }
  headers.set(REQUEST_ID_HEADER, context.requestId);

  return new NextResponse(JSON.stringify(envelope), {
    status,
    headers,
  }) as NextResponse<ApiSuccess<TData>>;
}

export type CreateCreatedResponseOptions = Readonly<{
  location?: string;
  headers?: HeadersInit;
}>;

export function createCreatedResponse<TData>(
  requestOrContext: Request | RequestContext,
  data: TData,
  options?: CreateCreatedResponseOptions,
): NextResponse<ApiSuccess<TData>> {
  const headers = new Headers(options?.headers);
  if (options?.location !== undefined && options.location.trim().length > 0) {
    headers.set('Location', options.location);
  }

  return createSuccessResponse(requestOrContext, data, {
    status: 201,
    headers,
  });
}

function isPaginationMeta(value: PaginationMeta | PaginationMetaInput): value is PaginationMeta {
  return (
    typeof value === 'object' &&
    value !== null &&
    'totalPages' in value &&
    typeof (value as PaginationMeta).page === 'number' &&
    typeof (value as PaginationMeta).limit === 'number' &&
    typeof (value as PaginationMeta).total === 'number' &&
    typeof (value as PaginationMeta).totalPages === 'number'
  );
}

export function createPaginatedResponse<TData>(
  requestOrContext: Request | RequestContext,
  data: TData,
  paginationInput: PaginationMeta | PaginationMetaInput,
  options?: Readonly<{ headers?: HeadersInit }>,
): NextResponse<ApiSuccess<TData>> {
  const pagination = isPaginationMeta(paginationInput)
    ? createPaginationMeta({
        page: paginationInput.page,
        limit: paginationInput.limit,
        total: paginationInput.total,
      })
    : createPaginationMeta(paginationInput);

  return createSuccessResponse(requestOrContext, data, {
    status: 200,
    pagination,
    ...(options?.headers !== undefined ? { headers: options.headers } : {}),
  });
}

export function createNoContentResponse(
  requestOrContext: Request | RequestContext,
  options?: Readonly<{ headers?: HeadersInit }>,
): NextResponse {
  const context = resolveRequestContext(requestOrContext);
  const headers = new Headers(options?.headers);
  headers.delete('content-type');
  headers.delete('content-length');
  if (!headers.has('Cache-Control')) {
    headers.set('Cache-Control', 'no-store');
  }
  headers.set(REQUEST_ID_HEADER, context.requestId);

  return new NextResponse(null, {
    status: 204,
    headers,
  });
}
