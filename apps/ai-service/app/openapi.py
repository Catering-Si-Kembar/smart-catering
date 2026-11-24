from __future__ import annotations

from typing import Any, Final

from pydantic import BaseModel

from app.contracts import (
    InsightGenerateData,
    InsightGenerateRequest,
    InsightGenerateResponse,
    InsightMetricsInput,
    InsightTopMenu,
    RagChatData,
    RagChatRequest,
    RagChatResponse,
    RagSourceItem,
    RelevanceMetadataData,
    RelevanceMetadataResponse,
    RelevanceModelMetrics,
    RelevancePredictData,
    RelevancePredictRequest,
    RelevancePredictResponse,
    SentimentBatchItemRequest,
    SentimentBatchItemResult,
    SentimentBatchRequest,
    SentimentBatchResponse,
    SentimentPredictData,
    SentimentPredictRequest,
    SentimentPredictResponse,
    SentimentProbabilities,
)
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
    RelevancePredictRequest,
    RelevancePredictData,
    RelevancePredictResponse,
    RelevanceModelMetrics,
    RelevanceMetadataData,
    RelevanceMetadataResponse,
    SentimentPredictRequest,
    SentimentProbabilities,
    SentimentPredictData,
    SentimentPredictResponse,
    SentimentBatchItemRequest,
    SentimentBatchRequest,
    SentimentBatchItemResult,
    SentimentBatchResponse,
    RagChatRequest,
    RagSourceItem,
    RagChatData,
    RagChatResponse,
    InsightTopMenu,
    InsightMetricsInput,
    InsightGenerateRequest,
    InsightGenerateData,
    InsightGenerateResponse,
)

_V1_EXAMPLES: Final[dict[str, dict[str, Any]]] = {
    "/api/v1/ml/predict-relevance": {
        "data": {
            "text": "Apakah ada paket nasi box ayam bakar untuk acara kantor 100 orang?",
            "label": "relevant",
            "is_relevant": True,
            "confidence": 0.942,
            "intent": None,
            "model_version": "relevance_lr_v1.0",
        },
        "meta": {"requestId": EXAMPLE_REQUEST_ID},
    },
    "/api/v1/ml/relevance/metadata": {
        "data": {
            "modelName": "relevance_classifier",
            "version": "1.0.0",
            "algorithm": "LogisticRegression",
            "classes": ["relevant", "out_of_domain"],
            "metrics": {"f1Score": 0.935, "accuracy": 0.941},
        },
        "meta": {"requestId": EXAMPLE_REQUEST_ID},
    },
    "/api/v1/ml/predict-sentiment": {
        "data": {
            "text": "Nasi liwetnya wangi pulen, ayam bakarnya enak dan tepat waktu.",
            "sentiment": "positive",
            "score": 0.965,
            "probabilities": {"positive": 0.965, "negative": 0.035},
        },
        "meta": {"requestId": EXAMPLE_REQUEST_ID},
    },
    "/api/v1/ml/predict-sentiment/batch": {
        "data": [
            {"id": "rev_01", "sentiment": "positive", "score": 0.952},
            {"id": "rev_02", "sentiment": "negative", "score": 0.884},
        ],
        "meta": {"requestId": EXAMPLE_REQUEST_ID},
    },
    "/api/v1/rag/chat": {
        "data": {
            "reply": (
                "Halo! Catering Si Kembar tentu melayani pesanan 50 nasi box. "
                "Untuk jadwal lusa, mohon pastikan pesanan segera dikonfirmasi dan "
                "pembayaran uang muka (DP) minimal 60% diselesaikan hari ini agar tim dapur "
                "kami dapat menyiapkan bahan baku tepat waktu."
            ),
            "is_relevant": True,
            "intent": None,
            "tools_called": ["search_catering_knowledge"],
            "sources": [
                {
                    "source": "faq.md",
                    "category": "pemesanan",
                    "chunk_id": "faq_order_01_c1",
                }
            ],
            "tokens_used": 185,
            "is_fallback": False,
        },
        "meta": {"requestId": EXAMPLE_REQUEST_ID},
    },
    "/api/v1/insight/generate": {
        "data": {
            "period": "November 2026",
            "executive_summary": (
                "Sepanjang November 2026 tercatat 38 pesanan dengan total omzet Rp24.500.000 "
                "dan tingkat penyelesaian 89.5% (34 dari 38 pesanan selesai)."
            ),
            "key_highlights": [
                "Tingkat penyelesaian pesanan 89.5% (34 dari 38 pesanan).",
                "Menu terlaris Nasi Box Ayam Lengkuas sebanyak 620 porsi.",
            ],
            "operational_recommendations": [
                "Lakukan penagihan pelunasan H-1 untuk 4 invoice belum lunas.",
                "Siapkan bahan baku untuk proyeksi minggu depan sebesar 450 porsi.",
            ],
            "model_used": "Qwen2.5-7B-Instruct-vLLM-Modal",
            "latency_ms": 3420,
            "is_fallback": False,
        },
        "meta": {"requestId": EXAMPLE_REQUEST_ID},
    },
}


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

        if path in {"/health", "/api/v1/health"} and method == "get":
            responses = {
                "405": {"$ref": "#/components/responses/MethodNotAllowedProblem"},
                "500": {"$ref": "#/components/responses/InternalServerErrorProblem"},
                **operation["responses"],
            }
            success = responses["200"]
            success_content = success.get("content", {}).get("application/json", {})
            return {
                **operation,
                "security": [],
                "parameters": [
                    *operation.get("parameters", []),
                    {"$ref": "#/components/parameters/RequestIdHeader"},
                ],
                "responses": {
                    **responses,
                    "200": {
                        **success,
                        "headers": {
                            "X-Request-Id": {"$ref": "#/components/headers/X-Request-Id"},
                            "X-Process-Time-Ms": {"$ref": "#/components/headers/X-Process-Time-Ms"},
                        },
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

        if path.startswith("/api/v1/") and path != "/api/v1/health":
            responses = {
                "400": {"$ref": "#/components/responses/BadRequestProblem"},
                "401": {"$ref": "#/components/responses/UnauthorizedProblem"},
                "405": {"$ref": "#/components/responses/MethodNotAllowedProblem"},
                "500": {"$ref": "#/components/responses/InternalServerErrorProblem"},
                "503": {"$ref": "#/components/responses/ServiceUnavailableProblem"},
                **operation["responses"],
            }
            if method == "post":
                responses["422"] = {"$ref": "#/components/responses/UnprocessableContentProblem"}
            if path in {"/api/v1/rag/chat", "/api/v1/insight/generate"}:
                responses["504"] = {"$ref": "#/components/responses/GatewayTimeoutProblem"}
            if path == "/api/v1/insight/generate":
                responses["403"] = {"$ref": "#/components/responses/ForbiddenProblem"}

            success = responses.get("200", {})
            success_content = success.get("content", {}).get("application/json", {})
            example_payload = _V1_EXAMPLES.get(
                path,
                {"data": {}, "meta": {"requestId": EXAMPLE_REQUEST_ID}},
            )

            existing_params = [
                p
                for p in operation.get("parameters", [])
                if not (
                    isinstance(p, dict)
                    and p.get("$ref")
                    in {
                        "#/components/parameters/RequestIdHeader",
                        "#/components/parameters/ActorRoleHeader",
                    }
                )
            ]
            existing_params.append({"$ref": "#/components/parameters/RequestIdHeader"})
            if path == "/api/v1/insight/generate":
                existing_params.append({"$ref": "#/components/parameters/ActorRoleHeader"})

            return {
                **operation,
                "security": [{"InternalTokenAuth": []}],
                "parameters": existing_params,
                "responses": {
                    **responses,
                    "200": {
                        **success,
                        "headers": {
                            "X-Request-Id": {"$ref": "#/components/headers/X-Request-Id"},
                            "X-Process-Time-Ms": {"$ref": "#/components/headers/X-Process-Time-Ms"},
                        },
                        "content": {
                            "application/json": {
                                **success_content,
                                "example": example_payload,
                            }
                        },
                    },
                },
            }

        responses = {
            "500": {"$ref": "#/components/responses/InternalServerErrorProblem"},
            **operation["responses"],
        }
        if "422" in responses:
            responses["422"] = {"$ref": "#/components/responses/UnprocessableContentProblem"}
        return {**operation, "responses": responses}

    return {
        path: {method: annotate(path, method, operation) for method, operation in item.items()}
        for path, item in paths.items()
    }


def build_openapi_schema(document: dict[str, Any]) -> dict[str, Any]:
    """Extend FastAPI's route-derived schema with the shared REST protocol components."""
    component_schemas = _collect_pydantic_component_schemas()
    request_id_header_ref = {"$ref": "#/components/headers/X-Request-Id"}
    process_time_header_ref = {"$ref": "#/components/headers/X-Process-Time-Ms"}

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

        headers: dict[str, Any] = {
            "X-Request-Id": request_id_header_ref,
            "X-Process-Time-Ms": process_time_header_ref,
        }
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
            "summary": "Smart Catering AI Service REST & OpenAPI 3.1 contract specification.",
            "description": (
                "REST & OpenAPI 3.1.0 foundation for the Smart Catering Python AI service "
                "(`@smart-catering/ai-service`).\n\n"
                "### Authentication & Docs Gate\n"
                "- Public liveness endpoints `/health` and `/api/v1/health` require no "
                "authentication (`security: []`).\n"
                "- Internal AI endpoints under `/api/v1/` are protected with `InternalTokenAuth` "
                "(`X-Internal-Token`).\n"
                "- Documentation routes (`GET /docs` and `GET /openapi.json`) are controlled by "
                "`DOCS_ENABLED` (default `true` in `development`/`test`, `false` in `production`). "
                "When enabled in `APP_ENV=production`, both routes require HTTP Basic "
                "authentication (`DocsBasicAuth`) with `DOCS_USERNAME` and a 32+ character "
                "`DOCS_PASSWORD` behind a TLS reverse proxy.\n\n"
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
            },
            {
                "name": "Relevance",
                "description": "Evaluate message domain relevance.",
            },
            {
                "name": "Sentiment",
                "description": "Customer feedback sentiment classification.",
            },
            {
                "name": "RAG",
                "description": "Interactive operational and SOP chat assistant.",
            },
            {
                "name": "Insights",
                "description": "Operational and executive business insight generation.",
            },
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
                "InternalTokenAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-Internal-Token",
                    "description": (
                        "Internal service secret token header for authenticated "
                        "service-to-service calls."
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
                "ActorRoleHeader": {
                    "name": "X-Actor-Role",
                    "in": "header",
                    "required": False,
                    "description": (
                        "Backend-verified actor role forwarded by Express (FS-08). Required as "
                        "`ADMIN` for `/api/v1/insight/generate` when internal authentication or "
                        "production mode is active; non-ADMIN values are rejected with 403."
                    ),
                    "schema": {
                        "type": "string",
                        "enum": ["ADMIN"],
                        "examples": ["ADMIN"],
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
                },
                "X-Process-Time-Ms": {
                    "description": "Total request processing duration in milliseconds.",
                    "schema": {
                        "type": "string",
                        "examples": ["1.42"],
                    },
                },
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
                        "X-Process-Time-Ms": process_time_header_ref,
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
                "ServiceUnavailableProblem": _problem_response_spec(
                    description=(
                        "AI capability or upstream inference model is temporarily unavailable."
                    ),
                    title="Service Unavailable",
                    status=503,
                    detail="The AI service capability is temporarily unavailable.",
                ),
                "GatewayTimeoutProblem": _problem_response_spec(
                    description="Upstream AI inference service or serverless worker timed out.",
                    title="Gateway Timeout",
                    status=504,
                    detail="The upstream AI inference service timed out.",
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
