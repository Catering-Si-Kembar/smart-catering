import type { z } from 'zod';
import { createBadRequestError, createValidationError } from './errors';
import { formatZodIssues } from './validation-issues';

export function validatePayload<TSchema extends z.ZodType>(
  schema: TSchema,
  input: unknown,
): z.output<TSchema> {
  const result = schema.safeParse(input);
  if (!result.success) {
    throw createValidationError(formatZodIssues(result.error));
  }
  return result.data;
}

function searchParamsToRecord(searchParams: URLSearchParams): Record<string, unknown> {
  const record: Record<string, unknown> = Object.create(null);
  for (const key of new Set(searchParams.keys())) {
    const values = searchParams.getAll(key);
    record[key] = values.length > 1 ? values : values[0];
  }
  return record;
}

export function validateQuery<TSchema extends z.ZodType>(
  schema: TSchema,
  source: Request | URL | URLSearchParams | Record<string, unknown>,
): z.output<TSchema> {
  let rawQuery: Record<string, unknown>;
  if (source instanceof Request) {
    const url = new URL(source.url, 'http://127.0.0.1');
    rawQuery = searchParamsToRecord(url.searchParams);
  } else if (source instanceof URL) {
    rawQuery = searchParamsToRecord(source.searchParams);
  } else if (source instanceof URLSearchParams) {
    rawQuery = searchParamsToRecord(source);
  } else {
    rawQuery = source;
  }

  return validatePayload(schema, rawQuery);
}

export async function parseJsonBody(request: Request): Promise<unknown> {
  let rawText: string;
  try {
    rawText = await request.text();
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

export async function parseAndValidateJsonBody<TSchema extends z.ZodType>(
  request: Request,
  schema: TSchema,
): Promise<z.output<TSchema>> {
  const parsedJson = await parseJsonBody(request);
  return validatePayload(schema, parsedJson);
}
