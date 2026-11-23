import type Joi from 'joi';
import type { Request as ExpressRequest } from 'express';
import { createBadRequestError, createValidationError } from './errors.js';
import { formatJoiIssues } from './validation-issues.js';

export function validatePayload<T>(schema: Joi.Schema<T>, input: unknown): T {
  const result = schema.validate(input, {
    abortEarly: false,
    convert: false,
    allowUnknown: false,
  });

  if (result.error) {
    throw createValidationError(formatJoiIssues(result.error));
  }

  return result.value as T;
}

function searchParamsToRecord(searchParams: URLSearchParams): Record<string, unknown> {
  const record: Record<string, unknown> = Object.create(null);
  for (const key of new Set(searchParams.keys())) {
    const values = searchParams.getAll(key);
    record[key] = values.length > 1 ? values : values[0];
  }
  return record;
}

export function validateQuery<T>(
  schema: Joi.Schema<T>,
  source: Request | ExpressRequest | URL | URLSearchParams | Record<string, unknown> | string,
): T {
  let rawQuery: Record<string, unknown>;

  if (typeof source === 'string') {
    const parsed = new URL(source, 'http://127.0.0.1');
    rawQuery = searchParamsToRecord(parsed.searchParams);
  } else if (source instanceof Request) {
    const parsed = new URL(source.url, 'http://127.0.0.1');
    rawQuery = searchParamsToRecord(parsed.searchParams);
  } else if (source instanceof URL) {
    rawQuery = searchParamsToRecord(source.searchParams);
  } else if (source instanceof URLSearchParams) {
    rawQuery = searchParamsToRecord(source);
  } else if (typeof source === 'object' && source !== null) {
    const candidate = source as Record<string, unknown>;
    if (typeof candidate['originalUrl'] === 'string' || typeof candidate['url'] === 'string') {
      const urlString = (candidate['originalUrl'] ?? candidate['url']) as string;
      const parsed = new URL(urlString, 'http://127.0.0.1');
      rawQuery = searchParamsToRecord(parsed.searchParams);
    } else {
      rawQuery = source as Record<string, unknown>;
    }
  } else {
    rawQuery = Object.create(null);
  }

  return validatePayload(schema, rawQuery);
}

export async function parseJsonBody(request: Request | ExpressRequest | string): Promise<unknown> {
  if (typeof request === 'string') {
    if (request.trim().length === 0) {
      throw createBadRequestError('The request body contains malformed JSON.');
    }
    try {
      return JSON.parse(request) as unknown;
    } catch {
      throw createBadRequestError('The request body contains malformed JSON.');
    }
  }

  if (typeof (request as Request).text === 'function') {
    let rawText: string;
    try {
      rawText = await (request as Request).text();
    } catch {
      throw createBadRequestError('The request body could not be read.');
    }

    if (rawText.trim().length === 0) {
      throw createBadRequestError('The request body contains malformed JSON.');
    }

    try {
      return JSON.parse(rawText) as unknown;
    } catch {
      throw createBadRequestError('The request body contains malformed JSON.');
    }
  }

  const expressReq = request as ExpressRequest;
  if (expressReq.body !== undefined) {
    if (expressReq.body === null) {
      throw createBadRequestError('The request body contains malformed JSON.');
    }
    if (typeof expressReq.body === 'string' && expressReq.body.trim().length === 0) {
      throw createBadRequestError('The request body contains malformed JSON.');
    }
    return expressReq.body;
  }

  throw createBadRequestError('The request body contains malformed JSON.');
}

export async function parseAndValidateJsonBody<T>(
  request: Request | ExpressRequest | string,
  schema: Joi.Schema<T>,
): Promise<T> {
  const parsedJson = await parseJsonBody(request);
  return validatePayload(schema, parsedJson);
}
