import type { Response as ExpressResponse, Request as ExpressRequest, NextFunction } from 'express';
import type { ProblemDetails, ValidationIssue } from '@smart-catering/types';
import Joi from 'joi';
import {
  REQUEST_ID_HEADER,
  type RequestContext,
  resolveRequestContext,
} from './request-context.js';
import { formatJoiIssues } from './validation-issues.js';

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

export function logServerFailure(
  error: unknown,
  requestOrContext: Request | ExpressRequest | RequestContext | object,
): void {
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

export function sendProblemResponse(
  res: ExpressResponse,
  problem: ProblemDetails,
  headers?: Readonly<Record<string, string>>,
): void {
  if (res.headersSent) {
    return;
  }
  res.status(problem.status);
  res.setHeader('Content-Type', PROBLEM_CONTENT_TYPE);
  if (!res.hasHeader('Cache-Control')) {
    res.setHeader('Cache-Control', 'no-store');
  }
  res.setHeader(REQUEST_ID_HEADER, problem.requestId);

  if (headers) {
    for (const [key, value] of Object.entries(headers)) {
      res.setHeader(key, value);
    }
  }

  if (res.req?.method === 'HEAD') {
    res.end();
    return;
  }

  res.send(JSON.stringify(problem));
}

export function handleApiError(
  error: unknown,
  req: ExpressRequest,
  res: ExpressResponse,
  next?: NextFunction,
): void {
  if (res.headersSent) {
    if (next) next(error);
    return;
  }

  const context = resolveRequestContext(req);

  if (error instanceof ApiHttpError) {
    if (error.status === 500) {
      logServerFailure(error, context);
    }
    const problem = buildProblemDetails({
      status: error.status,
      detail: error.detail,
      ...(error.errors !== undefined ? { errors: error.errors } : {}),
      instance: context.instance,
      requestId: context.requestId,
    });
    sendProblemResponse(res, problem, error.headers);
    return;
  }

  if (Joi.isError(error)) {
    const problem = buildProblemDetails({
      status: 422,
      detail: DEFAULT_PROBLEM_DETAILS[422],
      errors: formatJoiIssues(error),
      instance: context.instance,
      requestId: context.requestId,
    });
    sendProblemResponse(res, problem);
    return;
  }

  if (
    error instanceof SyntaxError &&
    (('status' in error && (error as { status: unknown }).status === 400) ||
      ('type' in error && (error as { type: unknown }).type === 'entity.parse.failed'))
  ) {
    const problem = buildProblemDetails({
      status: 400,
      detail: 'The request body contains malformed JSON.',
      instance: context.instance,
      requestId: context.requestId,
    });
    sendProblemResponse(res, problem);
    return;
  }

  logServerFailure(error, context);
  const problem = buildProblemDetails({
    status: 500,
    detail: DEFAULT_PROBLEM_DETAILS[500],
    instance: context.instance,
    requestId: context.requestId,
  });
  sendProblemResponse(res, problem);
}
