import type { PaginationMeta, ValidationIssue } from '@smart-catering/types';
import { createValidationError } from './errors';

export const DEFAULT_PAGE = 1;
export const DEFAULT_LIMIT = 20;
export const MAX_LIMIT = 100;
export const MAX_SAFE_PAGINATION_INT = 9_007_199_254_740_991;

const NON_DECIMAL_DIGITS_REGEX = /[^0-9]/;

export type PaginationQuery = Readonly<{
  page: number;
  limit: number;
  offset: number;
}>;

export type PaginationQueryInput = Readonly<{
  page?: unknown;
  limit?: unknown;
}>;

export type PaginationMetaInput = Readonly<{
  page?: unknown;
  limit?: unknown;
  total: unknown;
}>;

/**
 * Parses a nonnegative safe integer from a JS number or a strict decimal digit string.
 * Rejects booleans, floats/fractions, negative numbers, -0, hex/scientific strings, and > MAX_SAFE_PAGINATION_INT.
 */
export function parseStrictSafeInteger(value: unknown): number | null {
  if (typeof value === 'number') {
    if (Object.is(value, -0) || !Number.isSafeInteger(value)) {
      return null;
    }
    if (value < 0 || value > MAX_SAFE_PAGINATION_INT) {
      return null;
    }
    return value;
  }

  if (typeof value === 'string') {
    if (value.length === 0 || NON_DECIMAL_DIGITS_REGEX.test(value)) {
      return null;
    }
    const parsed = Number(value);
    return Number.isSafeInteger(parsed) ? parsed : null;
  }

  return null;
}

function extractRawQueryParams(input?: PaginationQueryInput | URLSearchParams | URL | Request): {
  rawPage: unknown;
  rawLimit: unknown;
} {
  if (input === undefined) {
    return { rawPage: undefined, rawLimit: undefined };
  }

  if (input instanceof Request) {
    return extractRawQueryParams(new URL(input.url, 'http://127.0.0.1').searchParams);
  }

  if (input instanceof URL) {
    return extractRawQueryParams(input.searchParams);
  }

  if (input instanceof URLSearchParams) {
    const pageValues = input.getAll('page');
    const limitValues = input.getAll('limit');
    return {
      rawPage:
        pageValues.length === 0 ? undefined : pageValues.length === 1 ? pageValues[0] : pageValues,
      rawLimit:
        limitValues.length === 0
          ? undefined
          : limitValues.length === 1
            ? limitValues[0]
            : limitValues,
    };
  }

  if (typeof input !== 'object' || input === null || Array.isArray(input)) {
    throw createValidationError([{ path: '$', code: 'invalid_value', message: 'Invalid value' }]);
  }

  return {
    rawPage: input.page,
    rawLimit: input.limit,
  };
}

function validatePageAndLimit(
  rawPage: unknown,
  rawLimit: unknown,
): {
  page: number;
  limit: number;
  offset: number;
  issues: ValidationIssue[];
} {
  const issues: ValidationIssue[] = [];
  let page = DEFAULT_PAGE;
  let limit = DEFAULT_LIMIT;
  let pageValid = true;
  let limitValid = true;

  if (rawPage !== undefined) {
    const parsedPage = parseStrictSafeInteger(rawPage);
    if (parsedPage === null || parsedPage < 1 || parsedPage > MAX_SAFE_PAGINATION_INT) {
      issues.push({ path: 'page', code: 'invalid_value', message: 'Invalid value' });
      pageValid = false;
    } else {
      page = parsedPage;
    }
  }

  if (rawLimit !== undefined) {
    const parsedLimit = parseStrictSafeInteger(rawLimit);
    if (parsedLimit === null || parsedLimit < 1 || parsedLimit > MAX_LIMIT) {
      issues.push({ path: 'limit', code: 'invalid_value', message: 'Invalid value' });
      limitValid = false;
    } else {
      limit = parsedLimit;
    }
  }

  let offset = 0;
  if (pageValid && limitValid) {
    const upperBound = page * limit;
    if (!Number.isSafeInteger(upperBound)) {
      issues.push({ path: 'page', code: 'invalid_value', message: 'Invalid value' });
    } else {
      offset = (page - 1) * limit;
    }
  }

  return { page, limit, offset, issues };
}

export function parsePaginationQuery(
  input?: PaginationQueryInput | URLSearchParams | URL | Request,
): PaginationQuery {
  const { rawPage, rawLimit } = extractRawQueryParams(input);
  const { page, limit, offset, issues } = validatePageAndLimit(rawPage, rawLimit);

  if (issues.length > 0) {
    throw createValidationError(issues);
  }

  return Object.freeze({ page, limit, offset });
}

export function createPaginationMeta(input: PaginationMetaInput): PaginationMeta {
  if (typeof input !== 'object' || input === null || Array.isArray(input)) {
    throw createValidationError([{ path: '$', code: 'invalid_value', message: 'Invalid value' }]);
  }

  const { page, limit, issues } = validatePageAndLimit(input.page, input.limit);
  const parsedTotal = parseStrictSafeInteger(input.total);

  if (parsedTotal === null || parsedTotal < 0 || parsedTotal > MAX_SAFE_PAGINATION_INT) {
    issues.push({ path: 'total', code: 'invalid_value', message: 'Invalid value' });
  }

  if (issues.length > 0 || parsedTotal === null) {
    throw createValidationError(issues);
  }

  const totalPages = parsedTotal === 0 ? 0 : Math.ceil(parsedTotal / limit);

  return Object.freeze({
    page,
    limit,
    total: parsedTotal,
    totalPages,
  });
}
