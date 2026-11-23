import type { ValidationIssue } from '@smart-catering/types';
import type Joi from 'joi';

export function formatValidationPath(pathSegments: readonly PropertyKey[]): string {
  if (pathSegments.length === 0) {
    return '$';
  }
  const normalized = pathSegments.map((segment) => String(segment)).filter(Boolean);
  return normalized.length > 0 ? normalized.join('.') : '$';
}

export function formatJoiIssues(joiError: Joi.ValidationError): readonly ValidationIssue[] {
  if (!joiError.details || joiError.details.length === 0) {
    return Object.freeze([
      Object.freeze({
        path: '$',
        code: 'invalid_value' as const,
        message: 'Invalid value' as const,
      }),
    ]);
  }

  const seenPaths = new Set<string>();
  const issues: ValidationIssue[] = [];
  for (const detail of joiError.details) {
    const formattedPath = formatValidationPath(detail.path);
    if (!seenPaths.has(formattedPath)) {
      seenPaths.add(formattedPath);
      issues.push(
        Object.freeze({
          path: formattedPath,
          code: 'invalid_value' as const,
          message: 'Invalid value' as const,
        }),
      );
    }
  }

  return Object.freeze(issues);
}
