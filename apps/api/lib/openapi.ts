import {
  OpenAPIRegistry,
  OpenApiGeneratorV31,
  extendZodWithOpenApi,
} from '@asteasolutions/zod-to-openapi';
import type { ApiReferenceConfiguration } from '@scalar/nextjs-api-reference';
import type { OpenAPIObject } from 'openapi3-ts/oas31';
import { z } from 'zod';
import { SCALAR_CDN_URL } from './docs-security';
import { DEFAULT_LIMIT, DEFAULT_PAGE, MAX_LIMIT, MAX_SAFE_PAGINATION_INT } from './pagination';
import { CANONICAL_UUID_REGEX } from './request-context';

extendZodWithOpenApi(z);

const EXAMPLE_REQUEST_ID = 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b';

export const RequestIdSchema = z.string().regex(CANONICAL_UUID_REGEX).openapi({
  description:
    'Canonical lowercase RFC 9562 UUID (versions 1–8) correlating the request and X-Request-Id header.',
  example: EXAMPLE_REQUEST_ID,
});

export const HealthDataSchema = z
  .object({
    status: z.literal('ok').openapi({ example: 'ok' }),
    service: z
      .enum(['api', 'worker', 'ai-service'])
      .openapi({ example: 'api', description: 'Logical service identifier.' }),
  })
  .strict()
  .openapi('HealthData', {
    description: 'Liveness status payload for Smart Catering services.',
    example: {
      status: 'ok',
      service: 'api',
    },
  });

export const PaginationMetaSchema = z
  .object({
    page: z.number().int().min(1).max(MAX_SAFE_PAGINATION_INT).openapi({
      description: '1-based page number.',
      example: DEFAULT_PAGE,
    }),
    limit: z.number().int().min(1).max(MAX_LIMIT).openapi({
      description: 'Maximum items per page (1..100).',
      example: DEFAULT_LIMIT,
    }),
    total: z.number().int().min(0).max(MAX_SAFE_PAGINATION_INT).openapi({
      description: 'Total matching records (0..9007199254740991).',
      example: 0,
    }),
    totalPages: z.number().int().min(0).max(MAX_SAFE_PAGINATION_INT).openapi({
      description: 'Total pages (0 when total is 0, otherwise ceil(total / limit)).',
      example: 0,
    }),
  })
  .strict()
  .openapi('PaginationMeta', {
    description: 'Standard pagination metadata attached to paginated collection responses.',
  });

export const PaginationQuerySchema = z
  .object({
    page: z.number().int().min(1).max(MAX_SAFE_PAGINATION_INT).default(DEFAULT_PAGE).openapi({
      description: '1-based page number (default 1).',
      example: DEFAULT_PAGE,
    }),
    limit: z.number().int().min(1).max(MAX_LIMIT).default(DEFAULT_LIMIT).openapi({
      description: 'Maximum items per page (default 20, max 100).',
      example: DEFAULT_LIMIT,
    }),
  })
  .strict()
  .openapi('PaginationQuery', {
    description: 'Reusable query parameter schema for paginated endpoints.',
  });

export const ApiMetaSchema = z
  .object({
    requestId: RequestIdSchema,
    pagination: PaginationMetaSchema.optional(),
  })
  .strict()
  .openapi('ApiMeta', {
    description: 'Standard response metadata containing requestId and optional pagination.',
    example: {
      requestId: EXAMPLE_REQUEST_ID,
    },
  });

export const HealthResponseSchema = z
  .object({
    data: HealthDataSchema,
    meta: ApiMetaSchema,
  })
  .strict()
  .openapi('HealthResponse', {
    description: 'Standard success envelope wrapping the API liveness payload.',
    example: {
      data: {
        status: 'ok',
        service: 'api',
      },
      meta: {
        requestId: EXAMPLE_REQUEST_ID,
      },
    },
  });

export const ValidationIssueSchema = z
  .object({
    path: z.string().min(1).openapi({
      description: 'Dot-delimited field path or "$" for root-level validation issues.',
      example: 'page',
    }),
    code: z.literal('invalid_value').openapi({
      description: 'Normalized machine-readable validation issue code.',
      example: 'invalid_value',
    }),
    message: z.literal('Invalid value').openapi({
      description: 'Sanitized public validation issue summary.',
      example: 'Invalid value',
    }),
  })
  .strict()
  .openapi('ValidationIssue', {
    description: 'Normalized field-level validation issue entry.',
  });

export const ProblemDetailsSchema = z
  .object({
    type: z.literal('about:blank').openapi({
      description: 'RFC 9457 problem type URI.',
      example: 'about:blank',
    }),
    title: z.string().openapi({
      description: 'Standard HTTP status phrase ("Unprocessable Content" for 422).',
      example: 'Not Found',
    }),
    status: z.number().int().min(400).max(599).openapi({
      description: 'HTTP status code.',
      example: 404,
    }),
    detail: z.string().openapi({
      description: 'Safe public problem description without internal details or reflected input.',
      example: 'The requested resource was not found.',
    }),
    instance: z.string().openapi({
      description: 'Request URL pathname without query parameters.',
      example: '/health',
    }),
    requestId: RequestIdSchema,
    errors: z.array(ValidationIssueSchema).optional().openapi({
      description: 'Normalized field validation errors (present on 422 Unprocessable Content).',
    }),
  })
  .strict()
  .openapi('ProblemDetails', {
    description: 'RFC 9457 Problem Details error response (application/problem+json).',
  });

function createOpenApiRegistry(): OpenAPIRegistry {
  const registry = new OpenAPIRegistry();

  registry.register('HealthData', HealthDataSchema);
  registry.register('PaginationMeta', PaginationMetaSchema);
  registry.register('PaginationQuery', PaginationQuerySchema);
  registry.register('ApiMeta', ApiMetaSchema);
  registry.register('HealthResponse', HealthResponseSchema);
  registry.register('ValidationIssue', ValidationIssueSchema);
  registry.register('ProblemDetails', ProblemDetailsSchema);

  registry.registerComponent('securitySchemes', 'DocsBasicAuth', {
    type: 'http',
    scheme: 'basic',
    description:
      'HTTP Basic authentication protecting /docs and /api/openapi when DOCS_ENABLED=true in production (NODE_ENV=production). Requires TLS termination at the reverse proxy. Public liveness GET /health does not require authentication.',
  });

  registry.registerComponent('headers', 'XRequestId', {
    description: 'Canonical lowercase UUID correlating the request and response.',
    required: true,
    schema: {
      type: 'string',
      format: 'uuid',
      example: EXAMPLE_REQUEST_ID,
    },
  });

  const problemStatuses = [
    {
      name: 'BadRequestProblem',
      status: 400,
      title: 'Bad Request',
      detail: 'The request body contains malformed JSON.',
    },
    {
      name: 'UnauthorizedProblem',
      status: 401,
      title: 'Unauthorized',
      detail:
        'Valid HTTP Basic authentication credentials are required to access API documentation.',
    },
    {
      name: 'ForbiddenProblem',
      status: 403,
      title: 'Forbidden',
      detail: 'You do not have permission to access this resource.',
    },
    {
      name: 'NotFoundProblem',
      status: 404,
      title: 'Not Found',
      detail: 'The requested resource was not found.',
    },
    {
      name: 'MethodNotAllowedProblem',
      status: 405,
      title: 'Method Not Allowed',
      detail: 'The HTTP method is not allowed for this resource.',
    },
    {
      name: 'UnprocessableContentProblem',
      status: 422,
      title: 'Unprocessable Content',
      detail: 'Request validation failed.',
      errors: [{ path: 'page', code: 'invalid_value', message: 'Invalid value' }],
    },
    {
      name: 'InternalServerErrorProblem',
      status: 500,
      title: 'Internal Server Error',
      detail: 'An unexpected error occurred.',
    },
  ] as const;

  for (const item of problemStatuses) {
    registry.registerComponent('responses', item.name, {
      description: `${item.status} ${item.title} (RFC 9457 Problem Details)`,
      headers: {
        'X-Request-Id': {
          $ref: '#/components/headers/XRequestId',
        },
      },
      content: {
        'application/problem+json': {
          schema: {
            $ref: '#/components/schemas/ProblemDetails',
          },
          example: {
            type: 'about:blank',
            title: item.title,
            status: item.status,
            detail: item.detail,
            instance: '/health',
            requestId: EXAMPLE_REQUEST_ID,
            ...('errors' in item ? { errors: item.errors } : {}),
          },
        },
      },
    });
  }

  registry.registerPath({
    method: 'get',
    path: '/health',
    operationId: 'getApiHealth',
    summary: 'Get API liveness status',
    description:
      'Public liveness endpoint for @smart-catering/api. Performs no external database, Chroma, WAHA, or AI service connections.',
    tags: ['Health'],
    security: [],
    request: {
      headers: z.object({
        'X-Request-Id': z.string().optional().openapi({
          description:
            'Optional UUID v1–v8 with the RFC variant. Valid values are normalized to lowercase; missing, invalid, or oversized values are replaced with a generated UUID v4.',
          example: EXAMPLE_REQUEST_ID,
        }),
      }),
    },
    responses: {
      200: {
        description: 'API service is alive and responding with the standard success envelope.',
        headers: {
          'X-Request-Id': {
            $ref: '#/components/headers/XRequestId',
          },
        },
        content: {
          'application/json': {
            schema: HealthResponseSchema,
            example: {
              data: {
                status: 'ok',
                service: 'api',
              },
              meta: {
                requestId: EXAMPLE_REQUEST_ID,
              },
            },
          },
        },
      },
      405: {
        $ref: '#/components/responses/MethodNotAllowedProblem',
      },
      500: {
        $ref: '#/components/responses/InternalServerErrorProblem',
      },
    },
  });

  registry.registerPath({
    method: 'get',
    path: '/api/openapi',
    operationId: 'getOpenApiSpecification',
    summary: 'Get raw OpenAPI 3.1.0 specification',
    description:
      'Protocol exception returning the raw OpenAPI 3.1.0 JSON document (not wrapped in { data, meta }) so Scalar and OpenAPI clients can consume the schema directly. Disabled by default in production; requires DocsBasicAuth when DOCS_ENABLED=true in production.',
    tags: ['Documentation'],
    security: [{ DocsBasicAuth: [] }],
    responses: {
      200: {
        description: 'Raw OpenAPI 3.1.0 JSON document.',
        headers: {
          'X-Request-Id': {
            $ref: '#/components/headers/XRequestId',
          },
        },
        content: {
          'application/json': {
            schema: {
              type: 'object',
              description: 'OpenAPI 3.1.0 specification object.',
            },
          },
        },
      },
      401: {
        $ref: '#/components/responses/UnauthorizedProblem',
      },
      404: {
        $ref: '#/components/responses/NotFoundProblem',
      },
      405: {
        $ref: '#/components/responses/MethodNotAllowedProblem',
      },
      500: {
        $ref: '#/components/responses/InternalServerErrorProblem',
      },
    },
  });

  registry.registerPath({
    method: 'get',
    path: '/docs',
    operationId: 'getScalarApiReference',
    summary: 'Render Scalar API Reference HTML',
    description:
      'Interactive HTML API documentation using the pinned Scalar classic bundle (https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.76.4) with agent, telemetry, auth persistence, remote proxy, and default fonts disabled. Requires internet access to load the pinned jsDelivr bundle. Disabled by default in production; requires DocsBasicAuth when DOCS_ENABLED=true in production.',
    tags: ['Documentation'],
    security: [{ DocsBasicAuth: [] }],
    responses: {
      200: {
        description: 'HTML document loading the pinned Scalar API Reference.',
        headers: {
          'X-Request-Id': {
            $ref: '#/components/headers/XRequestId',
          },
        },
        content: {
          'text/html': {
            schema: {
              type: 'string',
            },
          },
        },
      },
      401: {
        $ref: '#/components/responses/UnauthorizedProblem',
      },
      404: {
        $ref: '#/components/responses/NotFoundProblem',
      },
      405: {
        $ref: '#/components/responses/MethodNotAllowedProblem',
      },
      500: {
        $ref: '#/components/responses/InternalServerErrorProblem',
      },
    },
  });

  return registry;
}

export function generateOpenApiDocument(): OpenAPIObject {
  const registry = createOpenApiRegistry();
  const generator = new OpenApiGeneratorV31(registry.definitions);

  return generator.generateDocument({
    openapi: '3.1.0',
    info: {
      title: 'Smart Catering API',
      version: '0.0.0',
      description:
        'Phase 0 REST contract for @smart-catering/api. Provides public liveness (/health), reusable RFC 9457 Problem Details error components, pagination metadata schemas, and environment-gated OpenAPI 3.1.0 / Scalar documentation.',
    },
    servers: [
      {
        url: '/',
        description: 'Current API origin',
      },
    ],
    tags: [
      {
        name: 'Health',
        description: 'Public liveness verification without external infrastructure dependencies.',
      },
      {
        name: 'Documentation',
        description: 'Environment-gated OpenAPI 3.1.0 specification and Scalar API Reference.',
      },
    ],
  });
}

export function buildScalarConfiguration(): Partial<ApiReferenceConfiguration> {
  return {
    url: '/api/openapi',
    cdn: SCALAR_CDN_URL,
    bundle: false,
    pageTitle: 'Smart Catering API Reference',
    agent: {
      disabled: true,
      hideAddApi: true,
    },
    mcp: {
      disabled: true,
    },
    telemetry: false,
    persistAuth: false,
    proxyUrl: '',
    withDefaultFonts: false,
    showDeveloperTools: 'never',
    hideClientButton: true,
  };
}
