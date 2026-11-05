import type { ValidationIssue } from '@smart-catering/types';
import type { z } from 'zod';

export function formatValidationPath(pathSegments: readonly PropertyKey[]): string {
  if (pathSegments.length === 0) {
    return '$';
  }
  const normalized = pathSegments.map((segment) => String(segment)).filter(Boolean);
  return normalized.length > 0 ? normalized.join('.') : '$';
}
export function formatZodIssues(zodError: z.ZodError): readonly ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  for (const issue of zodError.issues) {
    const baseSegments = issue.path.map((segment) => String(segment)).filter(Boolean);
    if (
      issue.code === 'unrecognized_keys' &&
      'keys' in issue &&
      Array.isArray(issue.keys) &&
      issue.keys.length > 0
    ) {
      for (const key of issue.keys) {
        const keySegments = [...baseSegments, String(key)];
        issues.push(
          Object.freeze({
            path: formatValidationPath(keySegments),
            code: 'invalid_value',
            message: 'Invalid value',
          }),
        );
      }
    } else {
      issues.push(
        Object.freeze({
          path: formatValidationPath(issue.path),
          code: 'invalid_value',
          message: 'Invalid value',
        }),
      );
    }
  }

  if (issues.length === 0) {
    issues.push(
      Object.freeze({
        path: '$',
        code: 'invalid_value',
        message: 'Invalid value',
      }),
    );
  }

  return Object.freeze(issues);
}
