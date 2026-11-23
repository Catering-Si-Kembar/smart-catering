import type { Response as ExpressResponse } from 'express';
import type { ApiMeta, ApiSuccess, PaginationMeta } from '@smart-catering/types';
import { type PaginationMetaInput, createPaginationMeta } from './pagination.js';
import {
  REQUEST_ID_HEADER,
  isRequestContext,
  normalizeRequestId,
  resolveRequestContext,
} from './request-context.js';

export const JSON_CONTENT_TYPE = 'application/json; charset=utf-8';

function resolveRequestId(requestOrContext: unknown): string {
  if (typeof requestOrContext === 'string') {
    return normalizeRequestId(requestOrContext);
  }
  if (isRequestContext(requestOrContext)) {
    return requestOrContext.requestId;
  }
  if (typeof requestOrContext === 'object' && requestOrContext !== null) {
    return resolveRequestContext(requestOrContext).requestId;
  }
  return normalizeRequestId();
}

export function createSuccessEnvelope<TData>(
  data: TData,
  requestOrContext: unknown,
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

export type SendSuccessOptions = Readonly<{
  status?: 200 | 201 | undefined;
  pagination?: PaginationMeta | undefined;
  headers?: Readonly<Record<string, string>> | undefined;
}>;

export function sendSuccess<TData>(
  res: ExpressResponse,
  data: TData,
  options?: SendSuccessOptions,
): void {
  const context = resolveRequestContext(res.req ?? res);
  const status = options?.status ?? 200;
  const envelope = createSuccessEnvelope(data, context, options?.pagination);

  res.status(status);
  res.setHeader('Content-Type', JSON_CONTENT_TYPE);
  if (!res.hasHeader('Cache-Control')) {
    res.setHeader('Cache-Control', 'no-store');
  }
  res.setHeader(REQUEST_ID_HEADER, context.requestId);

  if (options?.headers) {
    for (const [key, value] of Object.entries(options.headers)) {
      res.setHeader(key, value);
    }
  }

  if (res.req?.method === 'HEAD') {
    res.end();
    return;
  }

  res.send(JSON.stringify(envelope));
}

export type SendCreatedOptions = Readonly<{
  location?: string | undefined;
  headers?: Readonly<Record<string, string>> | undefined;
}>;

export function sendCreated<TData>(
  res: ExpressResponse,
  data: TData,
  options?: SendCreatedOptions,
): void {
  const headers: Record<string, string> = { ...(options?.headers ?? {}) };
  if (options?.location !== undefined && options.location.trim().length > 0) {
    headers['Location'] = options.location;
  }

  sendSuccess(res, data, {
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

export function sendPaginated<TData>(
  res: ExpressResponse,
  data: TData,
  paginationInput: PaginationMeta | PaginationMetaInput,
  options?: Readonly<{ headers?: Readonly<Record<string, string>> | undefined }>,
): void {
  const pagination = isPaginationMeta(paginationInput)
    ? createPaginationMeta({
        page: paginationInput.page,
        limit: paginationInput.limit,
        total: paginationInput.total,
      })
    : createPaginationMeta(paginationInput);

  sendSuccess(res, data, {
    status: 200,
    pagination,
    ...(options?.headers !== undefined ? { headers: options.headers } : {}),
  });
}

export function sendNoContent(
  res: ExpressResponse,
  options?: Readonly<{ headers?: Readonly<Record<string, string>> | undefined }>,
): void {
  const context = resolveRequestContext(res.req ?? res);

  res.status(204);
  res.removeHeader('content-type');
  res.removeHeader('content-length');

  if (!res.hasHeader('Cache-Control')) {
    res.setHeader('Cache-Control', 'no-store');
  }
  res.setHeader(REQUEST_ID_HEADER, context.requestId);

  if (options?.headers) {
    for (const [key, value] of Object.entries(options.headers)) {
      const lower = key.toLowerCase();
      if (lower !== 'content-type' && lower !== 'content-length') {
        res.setHeader(key, value);
      }
    }
  }

  res.removeHeader('content-type');
  res.removeHeader('content-length');
  res.end();
}
