from __future__ import annotations

from typing import Any, Final

from pydantic import BaseModel

from app.docs import SCALAR_CDN_URL
from app.errors import PROBLEM_JSON_MEDIA_TYPE
from app.schemas import (
    ApiMeta,
    HealthData,
    HealthResponse,
    PaginationMeta,
    ProblemDetails,
    ValidationIssue,
)

OPENAPI_VERSION: Final[str] = "3.1.0"
EXAMPLE_REQUEST_ID: Final[str] = "01941234-5678-7abc-8def-0123456789ab"

_SCHEMA_MODELS: Final[tuple[type[BaseModel], ...]] = (
    HealthData,
    PaginationMeta,
    ApiMeta,
    HealthResponse,
    ValidationIssue,
    ProblemDetails,
)


def _collect_pydantic_component_schemas() -> dict[str, Any]:
    schemas: dict[str, Any] = {}
    for model_cls in _SCHEMA_MODELS:
        raw_schema = model_cls.model_json_schema(ref_template="#/components/schemas/{model}")
        defs = raw_schema.pop("$defs", None)
        if isinstance(defs, dict):
            for def_name, def_schema in defs.items():
                schemas.setdefault(def_name, def_schema)
        schemas[model_cls.__name__] = raw_schema
    return schemas


def _add_protocol_responses(paths: dict[str, Any]) -> dict[str, Any]:
    def annotate(path: str, method: str, operation: Any) -> Any:
        if not isinstance(operation, dict) or "responses" not in operation:
            return operation
        responses = {
            "500": {"$ref": "#/components/responses/InternalServerErrorProblem"},
            **operation["responses"],
        }
        if "422" in responses:
            responses = {
                **responses,
                "422": {"$ref": "#/components/responses/UnprocessableContentProblem"},
            }
        if path != "/health" or method != "get":
            return {**operation, "responses": responses}
        success = responses["200"]
        success_content = success["content"]["application/json"]
        return {
            **operation,
            "security": [],
            "parameters": [
                *operation.get("parameters", []),
                {"$ref": "#/components/parameters/RequestIdHeader"},
            ],
            "responses": {
                **responses,
                "405": {"$ref": "#/components/responses/MethodNotAllowedProblem"},
                "200": {
                    **success,
                    "headers": {"X-Request-Id": {"$ref": "#/components/headers/X-Request-Id"}},
                    "content": {
                        "application/json": {
                            **success_content,
                            "example": {
                                "data": {"status": "ok", "service": "ai-service"},
                                "meta": {"requestId": EXAMPLE_REQUEST_ID},
                            },
                        }
                    },
                },
            },
        }

    return {
        path: {method: annotate(path, method, operation) for method, operation in item.items()}
        for path, item in paths.items()
    }


def build_openapi_schema(document: dict[str, Any]) -> dict[str, Any]:
    """Extend FastAPI's route-derived schema with the shared REST protocol components."""
    component_schemas = _collect_pydantic_component_schemas()
    request_id_header_ref = {"$ref": "#/components/headers/X-Request-Id"}

    def _problem_response_spec(
        *,
        description: str,
        title: str,
        status: int,
        detail: str,
        instance: str = "/health",
        errors: list[dict[str, str]] | None = None,
        extra_headers: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        example_body: dict[str, Any] = {
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": instance,
            "requestId": EXAMPLE_REQUEST_ID,
        }
        if errors is not None:
            example_body["errors"] = errors

        headers: dict[str, Any] = {"X-Request-Id": request_id_header_ref}
        if extra_headers:
            headers.update(extra_headers)

        return {
            "description": description,
            "headers": headers,
            "content": {
                PROBLEM_JSON_MEDIA_TYPE: {
                    "schema": {"$ref": "#/components/schemas/ProblemDetails"},
                    "example": example_body,
                }
            },
        }

    return {
        **document,
        "openapi": OPENAPI_VERSION,
        "info": {
            **document["info"],
            "summary": "Phase 0 Python FastAPI REST & OpenAPI 3.1 foundation.",
            "description": (
                "REST & OpenAPI 3.1.0 foundation for the Smart Catering Python AI service "
                "(`@smart-catering/ai-service`).\n\n"
                "### Authentication & Docs Gate\n"
                "- `GET /health` is a public liveness endpoint (`security: []`) that performs "
                "no external database or Chroma connections.\n"
                "- Documentation routes (`GET /docs` and `GET /openapi.json`) are controlled by "
                "`DOCS_ENABLED` (default `true` in `development`/`test`, `false` in `production`). "
                "When enabled in `APP_ENV=production`, both routes require HTTP Basic "
                "authentication (`DocsBasicAuth`) with `DOCS_USERNAME` and a 32+ character "
                "`DOCS_PASSWORD` behind a TLS reverse proxy. No business JWT/session auth is "
                "implemented in Phase 0.\n\n"
                "### Scalar UI & Pinned CDN Notice\n"
                f"- `/docs` loads the pinned classic bundle `{SCALAR_CDN_URL}` with telemetry, "
                "AI agent chat, remote proxy, localStorage auth persistence, and external Google "
                "Fonts disabled. Browser access to `cdn.jsdelivr.net` is required to render the "
                "interactive UI, while HTTP Basic credentials remain scoped strictly to this "
                "origin."
            ),
        },
        "servers": [
            {
                "url": "/",
                "description": "Current AI service origin",
            }
        ],
        "tags": [
            {
                "name": "System",
                "description": "Public service liveness and operational diagnostics.",
            }
        ],
        "paths": _add_protocol_responses(document.get("paths", {})),
        "components": {
            **document.get("components", {}),
            "securitySchemes": {
                **document.get("components", {}).get("securitySchemes", {}),
                "DocsBasicAuth": {
                    "type": "http",
                    "scheme": "basic",
                    "description": (
                        "Production documentation gate HTTP Basic authentication "
                        "(`DOCS_USERNAME` / `DOCS_PASSWORD`, minimum 32 characters) protecting "
                        "`/docs` and `/openapi.json` when `APP_ENV=production` and "
                        "`DOCS_ENABLED=true` behind a TLS reverse proxy."
                    ),
                },
            },
            "parameters": {
                "RequestIdHeader": {
                    "name": "X-Request-Id",
                    "in": "header",
                    "required": False,
                    "description": (
                        "Optional canonical UUID (versions 1-8, RFC variant). Valid UUIDs are "
                        "preserved in lowercase; missing, malformed, or oversize values are "
                        "replaced with a fresh UUIDv4."
                    ),
                    "schema": {
                        "type": "string",
                        "format": "uuid",
                        "examples": [EXAMPLE_REQUEST_ID],
                    },
                },
                "PageQueryParam": {
                    "name": "page",
                    "in": "query",
                    "required": False,
                    "description": "1-based page number (default 1, positive safe integer).",
                    "schema": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 9_007_199_254_740_991,
                        "default": 1,
                    },
                },
                "LimitQueryParam": {
                    "name": "limit",
                    "in": "query",
                    "required": False,
                    "description": "Maximum items per page (default 20, range 1..100).",
                    "schema": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 20,
                    },
                },
            },
            "headers": {
                "X-Request-Id": {
                    "description": (
                        "Canonical lowercase UUID correlated with `meta.requestId` or "
                        "`ProblemDetails.requestId`."
                    ),
                    "schema": {
                        "type": "string",
                        "format": "uuid",
                        "examples": [EXAMPLE_REQUEST_ID],
                    },
                }
            },
            "schemas": {
                **component_schemas,
                **document.get("components", {}).get("schemas", {}),
            },
            "responses": {
                "NoContent204": {
                    "description": "204 No Content response with empty body and X-Request-Id.",
                    "headers": {
                        "X-Request-Id": request_id_header_ref,
                    },
                },
                "BadRequestProblem": _problem_response_spec(
                    description="Malformed JSON syntax or unparseable request payload.",
                    title="Bad Request",
                    status=400,
                    detail="Malformed JSON request body.",
                ),
                "UnauthorizedProblem": _problem_response_spec(
                    description="Missing or invalid authentication credentials.",
                    title="Unauthorized",
                    status=401,
                    detail="Authentication credentials are required or invalid.",
                    instance="/docs",
                    extra_headers={
                        "WWW-Authenticate": {
                            "description": (
                                "HTTP Basic authentication challenge for protected docs routes."
                            ),
                            "schema": {
                                "type": "string",
                                "examples": ['Basic realm="Smart Catering Docs", charset="UTF-8"'],
                            },
                        }
                    },
                ),
                "ForbiddenProblem": _problem_response_spec(
                    description="Authenticated caller lacks permission for the requested resource.",
                    title="Forbidden",
                    status=403,
                    detail="You do not have permission to access this resource.",
                ),
                "NotFoundProblem": _problem_response_spec(
                    description="Requested route or disabled documentation endpoint was not found.",
                    title="Not Found",
                    status=404,
                    detail="The requested resource was not found.",
                ),
                "MethodNotAllowedProblem": _problem_response_spec(
                    description="HTTP method is not supported for this endpoint.",
                    title="Method Not Allowed",
                    status=405,
                    detail="The HTTP method is not allowed for this resource.",
                ),
                "UnprocessableContentProblem": _problem_response_spec(
                    description="Structurally valid request failed schema validation.",
                    title="Unprocessable Content",
                    status=422,
                    detail="Request validation failed.",
                    errors=[
                        {
                            "path": "page",
                            "code": "invalid_value",
                            "message": "Invalid value",
                        }
                    ],
                ),
                "InternalServerErrorProblem": _problem_response_spec(
                    description="Unexpected server or configuration error with details redacted.",
                    title="Internal Server Error",
                    status=500,
                    detail="An unexpected error occurred.",
                ),
            },
        },
    }
