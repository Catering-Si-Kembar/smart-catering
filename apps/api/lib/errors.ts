import { NextResponse } from 'next/server';
import type { ProblemDetails, ValidationIssue } from '@smart-catering/types';
import { z } from 'zod';
import { REQUEST_ID_HEADER, type RequestContext, resolveRequestContext } from './request-context';
import { formatZodIssues } from './validation-issues';

export const PROBLEM_CONTENT_TYPE = 'application/problem+json; charset=utf-8';

export type ProblemStatus = 400 | 401 | 403 | 404 | 405 | 422 | 500;

export const PROBLEM_TITLES: Readonly<Record<ProblemStatus, string>> = Object.freeze({
  400: 'Bad Request',
  401: 'Unauthorized',
  403: 'Forbidden',
  404: 'Not Found',
  405: 'Method Not Allowed',
  422: 'Unprocessable Content',
  500: 'Internal Server Error',
});

export const DEFAULT_PROBLEM_DETAILS: Readonly<Record<ProblemStatus, string>> = Object.freeze({
  400: 'The request payload or parameters could not be parsed.',
  401: 'Authentication is required to access this resource.',
  403: 'You do not have permission to access this resource.',
  404: 'The requested resource was not found.',
  405: 'The HTTP method is not allowed for this resource.',
  422: 'Request validation failed.',
  500: 'An unexpected error occurred.',
});

export function isProblemStatus(status: number): status is ProblemStatus {
  return (
    status === 400 ||
    status === 401 ||
    status === 403 ||
    status === 404 ||
    status === 405 ||
    status === 422 ||
    status === 500
  );
}

export function normalizeProblemStatus(status: number): ProblemStatus {
  return isProblemStatus(status) ? status : 500;
}

export function sanitizeValidationIssues(
  issues?: readonly ValidationIssue[],
): readonly ValidationIssue[] | undefined {
  if (!issues || issues.length === 0) {
    return undefined;
  }
  return Object.freeze(
    issues.map((issue) =>
      Object.freeze({
        path: typeof issue.path === 'string' && issue.path.trim().length > 0 ? issue.path : '$',
        code: 'invalid_value' as const,
        message: 'Invalid value' as const,
      }),
    ),
  );
}

export type ApiHttpErrorOptions = Readonly<{
  status: ProblemStatus;
  detail?: string;
  errors?: readonly ValidationIssue[];
  headers?: Readonly<Record<string, string>>;
}>;

export class ApiHttpError extends Error {
  public readonly status: ProblemStatus;
  public readonly title: string;
  public readonly detail: string;
  public readonly errors?: readonly ValidationIssue[];
  public readonly headers?: Readonly<Record<string, string>>;

  public constructor(options: ApiHttpErrorOptions) {
    const normalizedStatus = normalizeProblemStatus(options.status);
    const safeDetail =
      normalizedStatus === 500
        ? DEFAULT_PROBLEM_DETAILS[500]
        : typeof options.detail === 'string' && options.detail.trim().length > 0
          ? options.detail
          : DEFAULT_PROBLEM_DETAILS[normalizedStatus];

    super(safeDetail);
    this.name = 'ApiHttpError';
    this.status = normalizedStatus;
    this.title = PROBLEM_TITLES[normalizedStatus];
    this.detail = safeDetail;

    const sanitizedErrors =
      normalizedStatus === 422 ? sanitizeValidationIssues(options.errors) : undefined;
    if (sanitizedErrors !== undefined) {
      this.errors = sanitizedErrors;
    }

    if (options.headers !== undefined) {
      this.headers = Object.freeze({ ...options.headers });
    }

    Object.setPrototypeOf(this, ApiHttpError.prototype);
  }
}

export function createBadRequestError(detail = DEFAULT_PROBLEM_DETAILS[400]): ApiHttpError {
  return new ApiHttpError({ status: 400, detail });
}

export function createUnauthorizedError(
  detail = DEFAULT_PROBLEM_DETAILS[401],
  headers?: Readonly<Record<string, string>>,
): ApiHttpError {
  return new ApiHttpError(
    headers !== undefined ? { status: 401, detail, headers } : { status: 401, detail },
  );
}

export function createForbiddenError(detail = DEFAULT_PROBLEM_DETAILS[403]): ApiHttpError {
  return new ApiHttpError({ status: 403, detail });
}

export function createNotFoundError(detail = DEFAULT_PROBLEM_DETAILS[404]): ApiHttpError {
  return new ApiHttpError({ status: 404, detail });
}

export function createMethodNotAllowedError(
  allowedMethods: readonly string[],
  detail = DEFAULT_PROBLEM_DETAILS[405],
): ApiHttpError {
  const allowValue = Array.from(
    new Set(
      allowedMethods.flatMap((method) => {
        const upper = method.trim().toUpperCase();
        return upper === 'GET' ? ['GET', 'HEAD'] : [upper];
      }),
    ),
  ).join(', ');

  return new ApiHttpError({
    status: 405,
    detail,
    headers: { Allow: allowValue },
  });
}

export function createValidationError(
  errors: readonly ValidationIssue[],
  detail = DEFAULT_PROBLEM_DETAILS[422],
): ApiHttpError {
  return new ApiHttpError({
    status: 422,
    detail,
    errors,
  });
}

export function createInternalServerError(): ApiHttpError {
  return new ApiHttpError({
    status: 500,
    detail: DEFAULT_PROBLEM_DETAILS[500],
  });
}

export type BuildProblemDetailsInput = Readonly<{
  status: number;
  detail?: string;
  instance: string;
  requestId: string;
  errors?: readonly ValidationIssue[];
}>;

export function buildProblemDetails(input: BuildProblemDetailsInput): ProblemDetails {
  const status = normalizeProblemStatus(input.status);
  const title = PROBLEM_TITLES[status];
  const detail =
    status === 500
      ? DEFAULT_PROBLEM_DETAILS[500]
      : typeof input.detail === 'string' && input.detail.trim().length > 0
        ? input.detail
        : DEFAULT_PROBLEM_DETAILS[status];

  const sanitizedErrors = status === 422 ? sanitizeValidationIssues(input.errors) : undefined;

  const base: ProblemDetails =
    sanitizedErrors !== undefined
      ? {
          type: 'about:blank',
          title,
          status,
          detail,
          instance: input.instance,
          requestId: input.requestId,
          errors: sanitizedErrors,
        }
      : {
          type: 'about:blank',
          title,
          status,
          detail,
          instance: input.instance,
          requestId: input.requestId,
        };

  return Object.freeze(base);
}

export type CreateProblemResponseOptions = Readonly<{
  status: number;
  detail?: string;
  errors?: readonly ValidationIssue[];
  headers?: HeadersInit;
}>;

export function createProblemResponse(
  requestOrContext: Request | RequestContext,
  options: CreateProblemResponseOptions,
): NextResponse<ProblemDetails> {
  const context = resolveRequestContext(requestOrContext);
  const status = normalizeProblemStatus(options.status);
  const problem = buildProblemDetails({
    status,
    ...(options.detail !== undefined ? { detail: options.detail } : {}),
    ...(options.errors !== undefined ? { errors: options.errors } : {}),
    instance: context.instance,
    requestId: context.requestId,
  });

  const headers = new Headers(options.headers);
  headers.set('Content-Type', PROBLEM_CONTENT_TYPE);
  if (!headers.has('Cache-Control')) {
    headers.set('Cache-Control', 'no-store');
  }
  headers.set(REQUEST_ID_HEADER, context.requestId);

  return new NextResponse(JSON.stringify(problem), {
    status,
    headers,
  }) as NextResponse<ProblemDetails>;
}

function logServerFailure(error: unknown, requestOrContext: Request | RequestContext): void {
  const context = resolveRequestContext(requestOrContext);
  console.error(
    JSON.stringify({
      event: 'api_request_failed',
      status: 500,
      requestId: context.requestId,
      instance: context.instance,
      errorType: error instanceof Error ? error.constructor.name : typeof error,
    }),
  );
}

export function handleApiError(
  error: unknown,
  requestOrContext: Request | RequestContext,
  defaultHeaders?: HeadersInit,
): NextResponse<ProblemDetails> {
  const mergedHeaders = new Headers(defaultHeaders);

  if (error instanceof ApiHttpError) {
    if (error.status === 500) logServerFailure(error, requestOrContext);
    if (error.headers) {
      for (const [key, value] of Object.entries(error.headers)) {
        mergedHeaders.set(key, value);
      }
    }
    return createProblemResponse(requestOrContext, {
      status: error.status,
      detail: error.detail,
      ...(error.errors !== undefined ? { errors: error.errors } : {}),
      headers: mergedHeaders,
    });
  }

  if (error instanceof z.ZodError) {
    return createProblemResponse(requestOrContext, {
      status: 422,
      detail: DEFAULT_PROBLEM_DETAILS[422],
      errors: formatZodIssues(error),
      headers: mergedHeaders,
    });
  }

  logServerFailure(error, requestOrContext);
  return createProblemResponse(requestOrContext, {
    status: 500,
    detail: DEFAULT_PROBLEM_DETAILS[500],
    headers: mergedHeaders,
  });
}
