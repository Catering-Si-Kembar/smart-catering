import type { OpenAPIObject } from 'openapi3-ts/oas31';
import { SCALAR_CDN_URL } from './docs-security.js';
import { DEFAULT_LIMIT, DEFAULT_PAGE, MAX_LIMIT, MAX_SAFE_PAGINATION_INT } from './pagination.js';
import { CANONICAL_UUID_REGEX } from './request-context.js';

const EXAMPLE_REQUEST_ID = 'b4b3cfc5-5a7e-4d0a-9c6f-740078c5158b';

export function generateOpenApiDocument(): OpenAPIObject {
  return {
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
    paths: {
      '/health': {
        get: {
          operationId: 'getApiHealth',
          summary: 'Get API liveness status',
          description:
            'Public liveness endpoint for @smart-catering/api. Performs no external database, Chroma, WAHA, or AI service connections.',
          tags: ['Health'],
          security: [],
          parameters: [
            {
              name: 'X-Request-Id',
              in: 'header',
              required: false,
              description:
                'Optional UUID v1–v8 with the RFC variant. Valid values are normalized to lowercase; missing, invalid, or oversized values are replaced with a generated UUID v4.',
              schema: {
                type: 'string',
                pattern: CANONICAL_UUID_REGEX.source,
                example: EXAMPLE_REQUEST_ID,
              },
            },
          ],
          responses: {
            '200': {
              description:
                'API service is alive and responding with the standard success envelope.',
              headers: {
                'X-Request-Id': {
                  $ref: '#/components/headers/XRequestId',
                },
              },
              content: {
                'application/json': {
                  schema: {
                    $ref: '#/components/schemas/HealthResponse',
                  },
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
            '405': {
              $ref: '#/components/responses/MethodNotAllowedProblem',
            },
            '500': {
              $ref: '#/components/responses/InternalServerErrorProblem',
            },
          },
        },
      },
      '/api/v1/health': {
        get: {
          operationId: 'getApiV1Health',
          summary: 'Get API v1 liveness status',
          description:
            'Public liveness endpoint for @smart-catering/api mounted under /api/v1 router.',
          tags: ['Health'],
          security: [],
          parameters: [
            {
              name: 'X-Request-Id',
              in: 'header',
              required: false,
              description:
                'Optional UUID v1–v8 with the RFC variant. Valid values are normalized to lowercase; missing, invalid, or oversized values are replaced with a generated UUID v4.',
              schema: {
                type: 'string',
                pattern: CANONICAL_UUID_REGEX.source,
                example: EXAMPLE_REQUEST_ID,
              },
            },
          ],
          responses: {
            '200': {
              description:
                'API v1 service is alive and responding with the standard success envelope.',
              headers: {
                'X-Request-Id': {
                  $ref: '#/components/headers/XRequestId',
                },
              },
              content: {
                'application/json': {
                  schema: {
                    $ref: '#/components/schemas/HealthResponse',
                  },
                },
              },
            },
            '405': {
              $ref: '#/components/responses/MethodNotAllowedProblem',
            },
            '500': {
              $ref: '#/components/responses/InternalServerErrorProblem',
            },
          },
        },
      },
      '/api/openapi': {
        get: {
          operationId: 'getOpenApiSpecification',
          summary: 'Get raw OpenAPI 3.1.0 specification',
          description:
            'Protocol exception returning the raw OpenAPI 3.1.0 JSON document (not wrapped in { data, meta }) so Scalar and OpenAPI clients can consume the schema directly. Disabled by default in production; requires DocsBasicAuth when DOCS_ENABLED=true in production.',
          tags: ['Documentation'],
          security: [{ DocsBasicAuth: [] }],
          responses: {
            '200': {
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
            '401': {
              $ref: '#/components/responses/UnauthorizedProblem',
            },
            '404': {
              $ref: '#/components/responses/NotFoundProblem',
            },
            '405': {
              $ref: '#/components/responses/MethodNotAllowedProblem',
            },
            '500': {
              $ref: '#/components/responses/InternalServerErrorProblem',
            },
          },
        },
      },
      '/docs': {
        get: {
          operationId: 'getScalarApiReference',
          summary: 'Render Scalar API Reference HTML',
          description:
            'Interactive HTML API documentation using the pinned Scalar classic bundle (https://cdn.jsdelivr.net/npm/@scalar/api-reference@1.76.4) with agent, telemetry, auth persistence, remote proxy, and default fonts disabled. Requires internet access to load the pinned jsDelivr bundle. Disabled by default in production; requires DocsBasicAuth when DOCS_ENABLED=true in production.',
          tags: ['Documentation'],
          security: [{ DocsBasicAuth: [] }],
          responses: {
            '200': {
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
            '401': {
              $ref: '#/components/responses/UnauthorizedProblem',
            },
            '404': {
              $ref: '#/components/responses/NotFoundProblem',
            },
            '405': {
              $ref: '#/components/responses/MethodNotAllowedProblem',
            },
            '500': {
              $ref: '#/components/responses/InternalServerErrorProblem',
            },
          },
        },
      },
    },
    components: {
      securitySchemes: {
        DocsBasicAuth: {
          type: 'http',
          scheme: 'basic',
          description:
            'HTTP Basic authentication protecting /docs and /api/openapi when DOCS_ENABLED=true in production (NODE_ENV=production). Requires TLS termination at the reverse proxy. Public liveness GET /health does not require authentication.',
        },
      },
      headers: {
        XRequestId: {
          description: 'Canonical lowercase UUID correlating the request and response.',
          required: true,
          schema: {
            type: 'string',
            format: 'uuid',
            example: EXAMPLE_REQUEST_ID,
          },
        },
      },
      schemas: {
        HealthData: {
          type: 'object',
          description: 'Liveness status payload for Smart Catering services.',
          properties: {
            status: {
              type: 'string',
              const: 'ok',
              example: 'ok',
            },
            service: {
              type: 'string',
              enum: ['api', 'worker', 'ai-service'],
              description: 'Logical service identifier.',
              example: 'api',
            },
          },
          required: ['status', 'service'],
          additionalProperties: false,
          example: {
            status: 'ok',
            service: 'api',
          },
        },
        PaginationMeta: {
          type: 'object',
          description: 'Standard pagination metadata attached to paginated collection responses.',
          properties: {
            page: {
              type: 'integer',
              minimum: 1,
              maximum: MAX_SAFE_PAGINATION_INT,
              description: '1-based page number.',
              example: DEFAULT_PAGE,
            },
            limit: {
              type: 'integer',
              minimum: 1,
              maximum: MAX_LIMIT,
              description: 'Maximum items per page (1..100).',
              example: DEFAULT_LIMIT,
            },
            total: {
              type: 'integer',
              minimum: 0,
              maximum: MAX_SAFE_PAGINATION_INT,
              description: 'Total matching records (0..9007199254740991).',
              example: 0,
            },
            totalPages: {
              type: 'integer',
              minimum: 0,
              maximum: MAX_SAFE_PAGINATION_INT,
              description: 'Total pages (0 when total is 0, otherwise ceil(total / limit)).',
              example: 0,
            },
          },
          required: ['page', 'limit', 'total', 'totalPages'],
          additionalProperties: false,
        },
        PaginationQuery: {
          type: 'object',
          description: 'Reusable query parameter schema for paginated endpoints.',
          properties: {
            page: {
              type: 'integer',
              minimum: 1,
              maximum: MAX_SAFE_PAGINATION_INT,
              default: DEFAULT_PAGE,
              description: '1-based page number (default 1).',
              example: DEFAULT_PAGE,
            },
            limit: {
              type: 'integer',
              minimum: 1,
              maximum: MAX_LIMIT,
              default: DEFAULT_LIMIT,
              description: 'Maximum items per page (default 20, max 100).',
              example: DEFAULT_LIMIT,
            },
          },
          additionalProperties: false,
        },
        ApiMeta: {
          type: 'object',
          description: 'Standard response metadata containing requestId and optional pagination.',
          properties: {
            requestId: {
              type: 'string',
              pattern: CANONICAL_UUID_REGEX.source,
              description:
                'Canonical lowercase RFC 9562 UUID (versions 1–8) correlating the request and X-Request-Id header.',
              example: EXAMPLE_REQUEST_ID,
            },
            pagination: {
              $ref: '#/components/schemas/PaginationMeta',
            },
          },
          required: ['requestId'],
          additionalProperties: false,
          example: {
            requestId: EXAMPLE_REQUEST_ID,
          },
        },
        HealthResponse: {
          type: 'object',
          description: 'Standard success envelope wrapping the API liveness payload.',
          properties: {
            data: {
              $ref: '#/components/schemas/HealthData',
            },
            meta: {
              $ref: '#/components/schemas/ApiMeta',
            },
          },
          required: ['data', 'meta'],
          additionalProperties: false,
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
        ValidationIssue: {
          type: 'object',
          description: 'Normalized field-level validation issue entry.',
          properties: {
            path: {
              type: 'string',
              minLength: 1,
              description: 'Dot-delimited field path or "$" for root-level validation issues.',
              example: 'page',
            },
            code: {
              type: 'string',
              const: 'invalid_value',
              description: 'Normalized machine-readable validation issue code.',
              example: 'invalid_value',
            },
            message: {
              type: 'string',
              const: 'Invalid value',
              description: 'Sanitized public validation issue summary.',
              example: 'Invalid value',
            },
          },
          required: ['path', 'code', 'message'],
          additionalProperties: false,
        },
        ProblemDetails: {
          type: 'object',
          description: 'RFC 9457 Problem Details error response (application/problem+json).',
          properties: {
            type: {
              type: 'string',
              const: 'about:blank',
              description: 'RFC 9457 problem type URI.',
              example: 'about:blank',
            },
            title: {
              type: 'string',
              description: 'Standard HTTP status phrase ("Unprocessable Content" for 422).',
              example: 'Not Found',
            },
            status: {
              type: 'integer',
              minimum: 400,
              maximum: 599,
              description: 'HTTP status code.',
              example: 404,
            },
            detail: {
              type: 'string',
              description:
                'Safe public problem description without internal details or reflected input.',
              example: 'The requested resource was not found.',
            },
            instance: {
              type: 'string',
              description: 'Request URL pathname without query parameters.',
              example: '/health',
            },
            requestId: {
              type: 'string',
              pattern: CANONICAL_UUID_REGEX.source,
              example: EXAMPLE_REQUEST_ID,
            },
            errors: {
              type: 'array',
              items: {
                $ref: '#/components/schemas/ValidationIssue',
              },
              description:
                'Normalized field validation errors (present on 422 Unprocessable Content).',
            },
          },
          required: ['type', 'title', 'status', 'detail', 'instance', 'requestId'],
          additionalProperties: false,
        },
      },
      responses: {
        BadRequestProblem: {
          description: '400 Bad Request (RFC 9457 Problem Details)',
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
                title: 'Bad Request',
                status: 400,
                detail: 'The request body contains malformed JSON.',
                instance: '/health',
                requestId: EXAMPLE_REQUEST_ID,
              },
            },
          },
        },
        UnauthorizedProblem: {
          description: '401 Unauthorized (RFC 9457 Problem Details)',
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
                title: 'Unauthorized',
                status: 401,
                detail:
                  'Valid HTTP Basic authentication credentials are required to access API documentation.',
                instance: '/docs',
                requestId: EXAMPLE_REQUEST_ID,
              },
            },
          },
        },
        ForbiddenProblem: {
          description: '403 Forbidden (RFC 9457 Problem Details)',
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
                title: 'Forbidden',
                status: 403,
                detail: 'You do not have permission to access this resource.',
                instance: '/health',
                requestId: EXAMPLE_REQUEST_ID,
              },
            },
          },
        },
        NotFoundProblem: {
          description: '404 Not Found (RFC 9457 Problem Details)',
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
                title: 'Not Found',
                status: 404,
                detail: 'The requested resource was not found.',
                instance: '/health',
                requestId: EXAMPLE_REQUEST_ID,
              },
            },
          },
        },
        MethodNotAllowedProblem: {
          description: '405 Method Not Allowed (RFC 9457 Problem Details)',
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
                title: 'Method Not Allowed',
                status: 405,
                detail: 'The HTTP method is not allowed for this resource.',
                instance: '/health',
                requestId: EXAMPLE_REQUEST_ID,
              },
            },
          },
        },
        UnprocessableContentProblem: {
          description: '422 Unprocessable Content (RFC 9457 Problem Details)',
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
                title: 'Unprocessable Content',
                status: 422,
                detail: 'Request validation failed.',
                instance: '/health',
                requestId: EXAMPLE_REQUEST_ID,
                errors: [{ path: 'page', code: 'invalid_value', message: 'Invalid value' }],
              },
            },
          },
        },
        InternalServerErrorProblem: {
          description: '500 Internal Server Error (RFC 9457 Problem Details)',
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
                title: 'Internal Server Error',
                status: 500,
                detail: 'An unexpected error occurred.',
                instance: '/health',
                requestId: EXAMPLE_REQUEST_ID,
              },
            },
          },
        },
      },
    },
  };
}

export function buildScalarConfiguration(): Record<string, unknown> {
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

export function renderScalarDocsHtml(config = buildScalarConfiguration()): string {
  const jsonConfig = JSON.stringify(config);
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Smart Catering API Reference</title>
  </head>
  <body>
    <div id="app"></div>
    <script src="${SCALAR_CDN_URL}"></script>
    <script>
      Scalar.createApiReference('#app', ${jsonConfig});
    </script>
  </body>
</html>`;
}
